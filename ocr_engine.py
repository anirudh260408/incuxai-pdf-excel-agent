"""
OCR Engine for Scanned Documents and Images.
Leverages PyMuPDF rendering, Pillow image enhancement, and Tesseract bounding-box table reconstruction.
Includes smart table boundary detection, scan noise removal, and layout alignment.
"""

from typing import List, Dict, Any, Optional, Tuple
import re
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import pytesseract
import pymupdf
import pandas as pd

from .detector import clean_cell_text, is_header_row, normalize_headers


class OCREngine:
    """Robust OCR engine designed for scanned documents, photos, and raster PDFs."""

    def __init__(self, dpi: int = 300):
        self.dpi = dpi

    def render_page_to_image(self, page: pymupdf.Page) -> Image.Image:
        """Render a PyMuPDF page to a high-resolution PIL Image."""
        zoom = self.dpi / 72.0
        mat = pymupdf.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat, alpha=False)
        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        return img

    def preprocess_image(self, img: Image.Image) -> Image.Image:
        """
        Enhance image contrast, convert to grayscale, and binarize for crisp OCR.
        """
        gray = img.convert("L")
        # Increase contrast
        enhancer = ImageEnhance.Contrast(gray)
        enhanced = enhancer.enhance(2.0)
        # Sharpen
        sharpened = enhanced.filter(ImageFilter.SHARPEN)
        return sharpened

    def extract_table_from_image(self, img: Image.Image) -> List[List[str]]:
        """
        Extract tabular grid from an image using multi-pass Tesseract OCR.
        Detects table headers, isolates table rows from headers/footers, and parses columns.
        """
        prep_img = self.preprocess_image(img)

        # Pass 1: Line-by-line structured layout with PSM 4
        try:
            txt = pytesseract.image_to_string(prep_img, config="--psm 4")
        except Exception:
            return []

        raw_lines = [l.strip() for l in txt.split("\n") if l.strip()]
        if not raw_lines:
            return []

        # Clean noise lines (pure punctuation, dashes, underscores, stray single chars)
        clean_lines = []
        for l in raw_lines:
            # Check if line is purely symbols/dashes/pipes
            stripped_syms = re.sub(r'[\s\|\—\-_=+\.\,\~\`\:\;\{\}\[\]\(\)]', '', l)
            if not stripped_syms or len(stripped_syms) < 2:
                continue
            clean_lines.append(l)

        if not clean_lines:
            return []

        # Find the Table Header Row
        header_idx = -1
        detected_headers = None

        for idx, line in enumerate(clean_lines):
            # Skip key-value document metadata lines (e.g. Invoice No: ... | Date: ...)
            if line.count(":") >= 2 or any(k in line.lower() for k in ["invoice no:", "bill no:", "date:"]):
                continue

            # Split line into candidate tokens
            parts = [p.strip() for p in re.split(r'\s{2,}|\s*\|\s*', line) if p.strip()]
            if len(parts) >= 3 and is_header_row(parts):
                header_idx = idx
                detected_headers = parts
                break

            # Or try standard header keyword count
            words = [w.lower() for w in re.split(r'[^a-zA-Z0-9]+', line) if w]
            common_kw = {"item", "description", "qty", "quantity", "rate", "price", "amount", "hsn", "total", "tax"}
            matches = [w for w in words if w in common_kw]
            if len(matches) >= 3:
                header_idx = idx
                sample_data = clean_lines[idx + 1] if idx + 1 < len(clean_lines) else None
                detected_headers = self._parse_header_line(line, sample_data)
                break

        # If no explicit header found, fallback to TSV bounding box extraction
        if header_idx == -1 or not detected_headers:
            return self._extract_table_bounding_boxes(prep_img)

        # Collect table rows starting from header_idx + 1
        table_rows: List[List[str]] = [detected_headers]
        num_cols = len(detected_headers)

        for l in clean_lines[header_idx + 1:]:
            # Check for table termination (footer notes, signatures, etc.)
            l_lower = l.lower()
            if any(term in l_lower for term in ["payment terms", "authorized signatory", "thank you", "terms & conditions"]):
                break

            # Clean line from stray pipes or brackets
            l_clean = re.sub(r'^[\|\}\—\=\s]+', '', l)
            l_clean = re.sub(r'[\|\}\—\=]+', ' ', l_clean).strip()
            tokens = l_clean.split()
            if not tokens:
                continue

            # Check if Total row
            if "total" in tokens[0].lower():
                total_row = ["TOTAL"] + ["" for _ in range(num_cols - 2)] + [tokens[-1]]
                table_rows.append(total_row)
                break

            # Parse regular data row matching column count
            parsed_row = self._parse_row_tokens(tokens, num_cols, detected_headers)
            if parsed_row and any(c.strip() for c in parsed_row):
                table_rows.append(parsed_row)

        return table_rows

    def _parse_header_line(self, line: str, sample_data_line: Optional[str] = None) -> List[str]:
        """Intelligently parse compound header string into distinct column names."""
        known_phrases = sorted([
            "Item #", "Item No", "Item Code", "Description of Goods", "Description",
            "HSN/SAC", "HSN Code", "Quantity", "Qty", "Unit Rate ($)", "Unit Rate",
            "Rate ($)", "Rate", "Unit Price", "Amount ($)", "Amount", "Total ($)", "Total"
        ], key=len, reverse=True)

        matches = []
        occupied = set()
        for p in known_phrases:
            for m in re.finditer(re.escape(p), line, re.IGNORECASE):
                span = set(range(m.start(), m.end()))
                if not span.intersection(occupied):
                    matches.append((m.start(), p))
                    occupied.update(span)

        if len(matches) >= 3:
            matches.sort(key=lambda x: x[0])
            headers = [m[1] for m in matches]

            # If sample data starts with an index/number and header doesn't start with Item, prepend Item #
            if sample_data_line:
                data_toks = sample_data_line.split()
                if data_toks and data_toks[0].isdigit() and not headers[0].lower().startswith("item"):
                    headers.insert(0, "Item #")

            return headers

        tokens = [t.strip() for t in re.split(r'\s{2,}|\s*\|\s*', line) if t.strip()]
        return tokens if len(tokens) >= 3 else line.split()

    def _parse_row_tokens(self, tokens: List[str], expected_cols: int, headers: List[str]) -> List[str]:
        """Map tokens to columns based on standard tabular schema."""
        if len(tokens) < 3:
            return []

        # If token count matches expected_cols exactly
        if len(tokens) == expected_cols:
            return tokens

        # If 6-column invoice schema: [Item, Description, HSN, Qty, Rate, Amount]
        if expected_cols == 6:
            item_no = tokens[0]
            amount = tokens[-1]
            rate = tokens[-2]
            
            # Find quantity: either tokens[-3] or clean numeric
            qty = tokens[-3]
            # If tokens[-3] has OCR noise (e.g. '8 iz'), clean it
            qty_match = re.search(r'\d+', qty)
            if qty_match:
                qty = qty_match.group(0)

            # HSN is usually 6-8 digits
            hsn = ""
            desc_tokens = []
            if len(tokens) >= 5:
                # Check tokens[-4]
                if re.match(r'^\d{4,8}$', tokens[-4]):
                    hsn = tokens[-4]
                    desc_tokens = tokens[1:-4]
                else:
                    desc_tokens = tokens[1:-3]
            else:
                desc_tokens = tokens[1:-2]

            desc = " ".join(desc_tokens)
            return [item_no, desc, hsn, qty, rate, amount]

        # Generic mapping: Left token, Right numbers, Middle text
        first_token = tokens[0]
        # Collect trailing numeric tokens
        numeric_trailing = []
        i = len(tokens) - 1
        while i > 0 and len(numeric_trailing) < (expected_cols - 2):
            tok = tokens[i]
            # Is numeric or currency
            num_clean = re.sub(r'[\$,₹€£%,\s]', '', tok)
            try:
                float(num_clean)
                numeric_trailing.insert(0, tok)
                i -= 1
            except ValueError:
                break

        middle_tokens = tokens[1:i+1]
        middle_text = " ".join(middle_tokens)

        row = [first_token, middle_text] + numeric_trailing
        # Pad if short
        while len(row) < expected_cols:
            row.insert(1, "")
        return row[:expected_cols]

    def _extract_table_bounding_boxes(self, prep_img: Image.Image) -> List[List[str]]:
        """Fallback TSV bounding box table reconstruction."""
        try:
            data = pytesseract.image_to_data(
                prep_img,
                config="--psm 6",
                output_type=pytesseract.Output.DATAFRAME
            )
        except Exception:
            return []

        data = data.dropna(subset=['text'])
        data['text'] = data['text'].astype(str).str.strip()
        data = data[data['text'].str.len() > 0]
        data = data[data['conf'] > 20]

        if data.empty:
            return []

        # Sort and group by line
        data = data.sort_values(by=['top', 'left']).reset_index(drop=True)
        lines = []
        vert_tol = 12 * (self.dpi / 150.0)

        for _, row in data.iterrows():
            word = {
                'text': row['text'],
                'left': float(row['left']),
                'top': float(row['top']),
                'width': float(row['width']),
                'right': float(row['left'] + row['width']),
            }
            assigned = False
            for ln in lines:
                avg_top = sum(w['top'] for w in ln) / len(ln)
                if abs(word['top'] - avg_top) <= vert_tol:
                    ln.append(word)
                    assigned = True
                    break
            if not assigned:
                lines.append([word])

        lines.sort(key=lambda ln: sum(w['top'] for w in ln) / len(ln))
        
        # Build rows
        table = []
        for ln in lines:
            ln_sorted = sorted(ln, key=lambda w: w['left'])
            row_cells = []
            cur_cell = [ln_sorted[0]['text']]
            for i in range(1, len(ln_sorted)):
                gap = ln_sorted[i]['left'] - ln_sorted[i-1]['right']
                if gap > 20 * (self.dpi / 150.0):
                    row_cells.append(" ".join(cur_cell))
                    cur_cell = [ln_sorted[i]['text']]
                else:
                    cur_cell.append(ln_sorted[i]['text'])
            row_cells.append(" ".join(cur_cell))
            if any(c.strip() for c in row_cells):
                table.append([clean_cell_text(c) for c in row_cells])

        return table

    def extract_from_page(self, page: pymupdf.Page) -> List[List[str]]:
        """Convenience method to render and OCR a PyMuPDF page directly."""
        img = self.render_page_to_image(page)
        return self.extract_table_from_image(img)
