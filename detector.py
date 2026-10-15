"""
Page type, table structure, and header detection module.
"""

from enum import Enum
from typing import List, Dict, Any, Tuple, Optional
import re
import pymupdf


class PageType(str, Enum):
    DIGITAL_TEXT = "digital_text"
    SCANNED_IMAGE = "scanned_image"
    HYBRID = "hybrid"


COMMON_HEADER_KEYWORDS = {
    "date", "time", "id", "no", "number", "code", "sku", "item", "description",
    "desc", "particulars", "name", "qty", "quantity", "units", "rate", "price",
    "cost", "amount", "debit", "credit", "balance", "total", "subtotal", "tax",
    "vat", "gst", "status", "category", "reference", "ref", "account", "txn",
    "value", "discount", "net", "gross", "type", "currency"
}


def classify_page(page: pymupdf.Page) -> Tuple[PageType, Dict[str, Any]]:
    """
    Classify whether a page is digital text or a scanned document/image.
    Returns the PageType and metadata.
    """
    text = page.get_text("text").strip()
    char_count = len(text)
    images = page.get_images(full=True)
    drawings = page.get_drawings()
    rect = page.rect
    page_area = rect.width * rect.height

    # Image area ratio
    image_area = 0.0
    for img in images:
        try:
            xref = img[0]
            bbox = page.get_image_bbox(img)
            if bbox:
                image_area += (bbox.width * bbox.height)
        except Exception:
            pass

    image_coverage = min(1.0, image_area / max(page_area, 1.0))

    if char_count < 40 and (len(images) > 0 or image_coverage > 0.4):
        ptype = PageType.SCANNED_IMAGE
    elif char_count > 100 and len(images) > 0 and image_coverage > 0.4:
        ptype = PageType.HYBRID
    else:
        ptype = PageType.DIGITAL_TEXT

    return ptype, {
        "char_count": char_count,
        "image_count": len(images),
        "drawings_count": len(drawings),
        "image_coverage": round(image_coverage, 3),
        "page_type": ptype.value
    }


def clean_cell_text(val: Any) -> str:
    """Clean and normalize cell text, collapsing redundant internal whitespace."""
    if val is None:
        return ""
    text = str(val).strip()
    text = re.sub(r'[\r\n]+', ' ', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    return text.strip()


def is_header_row(row: List[str], candidate_rows: Optional[List[List[str]]] = None) -> bool:
    """
    Heuristic to determine if a row is a table header:
    1. High proportion of non-empty string cells
    2. Low proportion of purely numeric cells
    3. Contains common header keywords
    4. Rejects key-value metadata rows with multiple colons
    """
    non_empty = [c for c in row if c and c.strip()]
    if not non_empty or len(non_empty) < 2:
        return False

    # Key-value document metadata check: e.g. "Invoice No: ...", "Date: ..."
    colon_cells = sum(1 for c in non_empty if ":" in c)
    if colon_cells >= 2 or (colon_cells >= 1 and len(non_empty) <= 3):
        return False

    # Check for numbers
    numeric_count = 0
    keyword_matches = 0

    for c in non_empty:
        c_clean = c.lower().strip()
        num_cleaned = re.sub(r'[$,₹€£%,\s]', '', c_clean)
        try:
            float(num_cleaned)
            numeric_count += 1
            continue
        except ValueError:
            pass

        words = re.split(r'[^a-zA-Z0-9]+', c_clean)
        if any(w in COMMON_HEADER_KEYWORDS for w in words):
            keyword_matches += 1

    numeric_ratio = numeric_count / len(non_empty)
    keyword_ratio = keyword_matches / len(non_empty)

    if numeric_ratio > 0.35:
        return False

    if keyword_matches >= 2 or keyword_ratio >= 0.25:
        return True

    all_text = all(re.search(r'[a-zA-Z]', c) for c in non_empty)
    if all_text and len(non_empty) >= 3:
        return True

    return False


def normalize_headers(headers: List[str]) -> List[str]:
    """
    Normalize header names: resolve duplicates, empty column names, and trim.
    """
    clean_headers: List[str] = []
    seen: Dict[str, int] = {}

    for i, h in enumerate(headers):
        h_str = clean_cell_text(h)
        if not h_str:
            h_str = f"Column_{i + 1}"
        
        # Deduplicate
        if h_str in seen:
            seen[h_str] += 1
            h_str = f"{h_str}_{seen[h_str]}"
        else:
            seen[h_str] = 1

        clean_headers.append(h_str)

    return clean_headers
