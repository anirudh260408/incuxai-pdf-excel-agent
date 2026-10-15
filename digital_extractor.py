"""
Digital PDF Table Extractor.
Uses pdfplumber and PyMuPDF with adaptive strategies for bordered (lattice) and borderless (stream) tables.
Handles 10+ column tables, multi-line headers, and dense tabular data.
"""

from typing import List, Dict, Any, Optional
import pdfplumber
import pymupdf
from .detector import clean_cell_text, is_header_row, normalize_headers


class DigitalTableExtractor:
    """High-precision table extractor for digital vector PDFs."""

    def __init__(self):
        # Adaptive extraction settings
        self.lattice_settings = {
            "vertical_strategy": "lines",
            "horizontal_strategy": "lines",
            "snap_tolerance": 3,
            "join_tolerance": 3,
            "edge_min_length": 3,
            "min_words_vertical": 1,
            "min_words_horizontal": 1,
            "intersection_tolerance": 3,
        }

        self.stream_settings = {
            "vertical_strategy": "text",
            "horizontal_strategy": "text",
            "snap_tolerance": 4,
            "join_tolerance": 3,
            "min_words_vertical": 2,
            "min_words_horizontal": 1,
        }

        self.hybrid_settings = {
            "vertical_strategy": "lines_strict",
            "horizontal_strategy": "text",
            "snap_tolerance": 3,
        }

    def extract_tables_from_plumber_page(self, page: pdfplumber.page.Page) -> List[List[List[str]]]:
        """
        Extract all candidate tables from a pdfplumber page using adaptive strategies.
        """
        tables_found: List[List[List[str]]] = []

        # Strategy 1: Lattice (explicit grid lines)
        try:
            raw_tables = page.extract_tables(self.lattice_settings)
            valid_tables = self._filter_valid_tables(raw_tables)
            if valid_tables:
                return valid_tables
        except Exception:
            pass

        # Strategy 2: Stream (text alignment heuristics)
        try:
            raw_tables = page.extract_tables(self.stream_settings)
            valid_tables = self._filter_valid_tables(raw_tables)
            if valid_tables:
                return valid_tables
        except Exception:
            pass

        # Strategy 3: Default pdfplumber extract_tables
        try:
            raw_tables = page.extract_tables()
            valid_tables = self._filter_valid_tables(raw_tables)
            if valid_tables:
                return valid_tables
        except Exception:
            pass

        return []

    def extract_with_pymupdf(self, fitz_page: pymupdf.Page) -> List[List[List[str]]]:
        """
        Fallback extraction using PyMuPDF's built-in find_tables() feature.
        """
        tables: List[List[List[str]]] = []
        try:
            tabs = fitz_page.find_tables()
            for tab in tabs:
                df = tab.extract()
                if df and len(df) > 1:
                    clean_grid = []
                    for row in df:
                        clean_row = [clean_cell_text(c) for c in row]
                        if any(c for c in clean_row):
                            clean_grid.append(clean_row)
                    if len(clean_grid) >= 2:
                        tables.append(clean_grid)
        except Exception:
            pass
        return tables

    def _filter_valid_tables(self, raw_tables: List[List[List[Any]]]) -> List[List[List[str]]]:
        """Filter and standardize raw table matrices."""
        valid_tables: List[List[List[str]]] = []

        for raw_tbl in raw_tables:
            if not raw_tbl or len(raw_tbl) < 2:
                continue

            cleaned_grid: List[List[str]] = []
            max_cols = 0

            for row in raw_tbl:
                cleaned_row = [clean_cell_text(cell) for cell in row]
                # If row is not completely empty
                if any(c for c in cleaned_row):
                    cleaned_grid.append(cleaned_row)
                    if len(cleaned_row) > max_cols:
                        max_cols = len(cleaned_row)

            # Ensure rectangular matrix
            if cleaned_grid and max_cols >= 2 and len(cleaned_grid) >= 2:
                padded_grid = []
                for row in cleaned_grid:
                    if len(row) < max_cols:
                        row = row + ["" for _ in range(max_cols - len(row))]
                    padded_grid.append(row[:max_cols])
                valid_tables.append(padded_grid)

        return valid_tables
