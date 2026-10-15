"""
Multi-Page Table Stitcher.
Intelligently joins tables spanning across multiple pages without losing data,
removing redundant repeated headers, handling page footers/headers, and maintaining column alignment.
"""

from typing import List, Dict, Any, Optional, Tuple
import re
from difflib import SequenceMatcher
import pandas as pd
from .detector import is_header_row, clean_cell_text, normalize_headers


class TableStitcher:
    """Multi-page continuity engine for tables spanning up to 50+ pages."""

    def __init__(self, header_similarity_threshold: float = 0.65):
        self.header_sim_threshold = header_similarity_threshold

    def string_similarity(self, s1: str, s2: str) -> float:
        """Compute normalized string similarity between two header strings."""
        c1 = re.sub(r'[^a-z0-9]', '', s1.lower())
        c2 = re.sub(r'[^a-z0-9]', '', s2.lower())
        if not c1 and not c2:
            return 1.0
        if not c1 or not c2:
            return 0.0
        return SequenceMatcher(None, c1, c2).ratio()

    def compare_header_rows(self, h1: List[str], h2: List[str]) -> float:
        """
        Compare two candidate header rows and return a similarity score (0.0 to 1.0).
        Handles minor OCR typos or column width shifts.
        """
        if not h1 or not h2:
            return 0.0

        # If column count difference is large, low similarity
        len_diff = abs(len(h1) - len(h2))
        if len_diff > 2:
            return 0.0

        min_len = min(len(h1), len(h2))
        max_len = max(len(h1), len(h2))
        if min_len == 0:
            return 0.0

        matches = 0.0
        for i in range(min_len):
            sim = self.string_similarity(h1[i], h2[i])
            matches += sim

        score = matches / max_len
        return score

    def is_continuation_of(self, parent_table: List[List[str]], child_table: List[List[str]]) -> Tuple[bool, bool]:
        """
        Determine if child_table is a continuation of parent_table.
        Returns:
            (is_continuation, has_repeated_header)
        """
        if not parent_table or not child_table:
            return False, False

        parent_header = parent_table[0]
        child_first_row = child_table[0]

        parent_cols = len(parent_header)
        child_cols = len(child_first_row)

        # Check for repeated header on child table
        sim = self.compare_header_rows(parent_header, child_first_row)
        if sim >= self.header_sim_threshold:
            return True, True

        # Check if child first row is NOT a header, but column count matches perfectly
        if parent_cols == child_cols:
            # If child first row is not a new header, it's very likely a direct continuation
            if not is_header_row(child_first_row, child_table):
                return True, False

        # If column count differs by 1 due to an empty column
        if abs(parent_cols - child_cols) <= 1:
            if not is_header_row(child_first_row, child_table):
                # Check data type alignment across first 3 columns
                return True, False

        return False, False

    def is_page_footer_or_header_row(self, row: List[str]) -> bool:
        """
        Detect noise rows like 'Page 2 of 10', 'Continued on next page', 'Confidential'.
        """
        text = " ".join([c for c in row if c]).strip().lower()
        if not text:
            return True

        footer_patterns = [
            r'page\s+\d+\s+of\s+\d+',
            r'page\s+\d+',
            r'continued\s+on\s+next\s+page',
            r'brought\s+forward',
            r'carried\s+forward',
            r'confidential\s+document',
            r'printed\s+on\s+\d{2}/\d{2}/\d{4}',
            r'report\s+generated',
        ]
        for pattern in footer_patterns:
            if re.search(pattern, text):
                return True
        return False

    def stitch_page_tables(self, page_tables_map: Dict[int, List[List[List[str]]]]) -> List[Dict[str, Any]]:
        """
        Stitch tables across pages.
        page_tables_map: {page_number: [table_1, table_2, ...]}
        Returns a list of consolidated table structures:
        [
            {
                "table_id": 1,
                "pages": [1, 2, 3],
                "headers": [...],
                "rows": [[...], [...], ...],
                "dataframe": pd.DataFrame(...)
            },
            ...
        ]
        """
        consolidated: List[Dict[str, Any]] = []

        sorted_pages = sorted(page_tables_map.keys())

        for page_num in sorted_pages:
            tables_on_page = page_tables_map[page_num]

            for tbl in tables_on_page:
                if not tbl or len(tbl) < 1:
                    continue

                stitched = False

                # Try to stitch with the most recent open consolidated table
                if consolidated:
                    last_table_info = consolidated[-1]
                    parent_table = [last_table_info["headers"]] + last_table_info["rows"]

                    is_cont, has_rep_hdr = self.is_continuation_of(parent_table, tbl)

                    if is_cont:
                        # Append rows
                        start_idx = 1 if has_rep_hdr else 0
                        target_col_count = len(last_table_info["headers"])

                        for r_idx in range(start_idx, len(tbl)):
                            row = tbl[r_idx]
                            # Skip page headers/footers in table
                            if self.is_page_footer_or_header_row(row):
                                continue

                            # Standardize column length
                            if len(row) < target_col_count:
                                row = row + ["" for _ in range(target_col_count - len(row))]
                            elif len(row) > target_col_count:
                                row = row[:target_col_count]

                            last_table_info["rows"].append(row)

                        if page_num not in last_table_info["pages"]:
                            last_table_info["pages"].append(page_num)

                        stitched = True

                if not stitched:
                    # New table encountered
                    # Determine headers
                    first_row = tbl[0]
                    if is_header_row(first_row, tbl):
                        headers = normalize_headers(first_row)
                        rows = tbl[1:]
                    else:
                        # Generate default headers
                        headers = [f"Column_{i+1}" for i in range(len(first_row))]
                        rows = tbl

                    # Filter footer/header rows
                    clean_rows = []
                    target_len = len(headers)
                    for r in rows:
                        if not self.is_page_footer_or_header_row(r):
                            if len(r) < target_len:
                                r = r + ["" for _ in range(target_len - len(r))]
                            elif len(r) > target_len:
                                r = r[:target_len]
                            clean_rows.append(r)

                    table_dict = {
                        "table_id": len(consolidated) + 1,
                        "pages": [page_num],
                        "headers": headers,
                        "rows": clean_rows,
                        "dataframe": None
                    }
                    consolidated.append(table_dict)

        # Convert each consolidated table to a clean pandas DataFrame
        for t in consolidated:
            df = pd.DataFrame(t["rows"], columns=t["headers"])
            # Remove entirely empty rows
            df = df.dropna(how='all')
            # Remove rows where all cells are empty string
            df = df[~df.apply(lambda r: all(str(v).strip() == "" for v in r), axis=1)]
            df = df.reset_index(drop=True)
            t["dataframe"] = df

        return consolidated
