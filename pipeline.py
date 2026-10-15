"""
End-to-End AI Agent Pipeline Orchestrator.
Streams up to 50+ page documents, automatically selects OCR vs Digital extraction,
stitches multi-page tables, audits data integrity, and outputs polished Excel workbooks.
"""

from typing import List, Dict, Any, Optional, Callable
import time
import os
import pymupdf
import pdfplumber
import pandas as pd

from .detector import classify_page, PageType
from .digital_extractor import DigitalTableExtractor
from .ocr_engine import OCREngine
from .table_stitcher import TableStitcher
from .validator import DataValidator, ValidationReport
from .excel_writer import ProfessionalExcelWriter


class ProcessResult:
    """Encapsulates the complete result of document processing."""

    def __init__(
        self,
        success: bool,
        source_path: str,
        output_excel_path: str,
        total_pages: int,
        tables_data: List[Dict[str, Any]],
        validation_reports: List[ValidationReport],
        page_types: Dict[int, str],
        elapsed_seconds: float,
        error_message: Optional[str] = None
    ):
        self.success = success
        self.source_path = source_path
        self.output_excel_path = output_excel_path
        self.total_pages = total_pages
        self.tables_data = tables_data
        self.validation_reports = validation_reports
        self.page_types = page_types
        self.elapsed_seconds = round(elapsed_seconds, 2)
        self.error_message = error_message

        # Aggregated Metrics
        self.total_tables = len(tables_data)
        self.total_rows = sum(len(t["dataframe"]) for t in tables_data) if tables_data else 0
        self.total_errors = sum(v.errors_count for v in validation_reports)
        self.total_warnings = sum(v.warnings_count for v in validation_reports)
        if validation_reports:
            self.overall_integrity_score = round(
                sum(v.integrity_score for v in validation_reports) / len(validation_reports), 1
            )
        else:
            self.overall_integrity_score = 100.0

    def summary_dict(self) -> Dict[str, Any]:
        return {
            "source": os.path.basename(self.source_path),
            "output_excel": self.output_excel_path,
            "total_pages": self.total_pages,
            "total_tables": self.total_tables,
            "total_rows": self.total_rows,
            "overall_integrity_score": f"{self.overall_integrity_score}%",
            "critical_errors": self.total_errors,
            "warnings": self.total_warnings,
            "processing_time": f"{self.elapsed_seconds}s",
            "page_breakdown": self.page_types
        }


class DocumentPipeline:
    """Master AI Document-to-Excel Conversion Agent."""

    def __init__(self):
        self.digital_extractor = DigitalTableExtractor()
        self.ocr_engine = OCREngine(dpi=300)
        self.stitcher = TableStitcher()
        self.validator = DataValidator()
        self.excel_writer = ProfessionalExcelWriter()

    def process_document(
        self,
        input_path: str,
        output_path: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> ProcessResult:
        """
        Main entrypoint: Converts a PDF or image into a structured Excel workbook.
        Supports up to 50+ pages with streaming batch processing.
        """
        start_time = time.time()
        input_path = os.path.abspath(input_path)

        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        if output_path is None:
            base_name = os.path.splitext(os.path.basename(input_path))[0]
            output_path = os.path.join(os.path.dirname(input_path), f"{base_name}_converted.xlsx")
        else:
            output_path = os.path.abspath(output_path)

        # Open PDF documents
        doc_fitz = pymupdf.open(input_path)
        total_pages = len(doc_fitz)
        page_types: Dict[int, str] = {}
        page_tables_map: Dict[int, List[List[List[str]]]] = {}

        # Open with pdfplumber if digital pages exist
        plumber_doc = None
        try:
            plumber_doc = pdfplumber.open(input_path)
        except Exception:
            pass

        try:
            # Process page by page (memory efficient streaming for up to 50+ pages)
            for page_idx in range(total_pages):
                page_num = page_idx + 1
                fitz_page = doc_fitz[page_idx]

                if progress_callback:
                    progress_callback(page_num, total_pages, f"Analyzing Page {page_num}/{total_pages}...")

                # 1. Classify page type
                ptype, pmeta = classify_page(fitz_page)
                page_types[page_num] = ptype.value

                tables_on_page: List[List[List[str]]] = []

                # 2. Extract based on classification
                if ptype == PageType.DIGITAL_TEXT and plumber_doc is not None:
                    try:
                        plumber_page = plumber_doc.pages[page_idx]
                        tables_on_page = self.digital_extractor.extract_tables_from_plumber_page(plumber_page)
                    except Exception:
                        pass

                    # Fallback to PyMuPDF table finder if plumber found nothing
                    if not tables_on_page:
                        tables_on_page = self.digital_extractor.extract_with_pymupdf(fitz_page)

                elif ptype == PageType.SCANNED_IMAGE:
                    if progress_callback:
                        progress_callback(page_num, total_pages, f"Running OCR Engine on Page {page_num}...")
                    ocr_table = self.ocr_engine.extract_from_page(fitz_page)
                    if ocr_table and len(ocr_table) >= 2:
                        tables_on_page = [ocr_table]

                else:  # HYBRID
                    if plumber_doc is not None:
                        try:
                            plumber_page = plumber_doc.pages[page_idx]
                            tables_on_page = self.digital_extractor.extract_tables_from_plumber_page(plumber_page)
                        except Exception:
                            pass
                    if not tables_on_page:
                        ocr_table = self.ocr_engine.extract_from_page(fitz_page)
                        if ocr_table and len(ocr_table) >= 2:
                            tables_on_page = [ocr_table]

                # Store extracted tables for this page
                if tables_on_page:
                    page_tables_map[page_num] = tables_on_page

            if progress_callback:
                progress_callback(total_pages, total_pages, "Stitching multi-page tables...")

            # 3. Stitch tables across pages
            stitched_tables = self.stitcher.stitch_page_tables(page_tables_map)

            # If no tables were identified, fallback to full text extraction into a grid
            if not stitched_tables:
                fallback_rows = []
                for p_idx in range(total_pages):
                    txt = doc_fitz[p_idx].get_text("text").strip()
                    for line in txt.split("\n"):
                        if line.strip():
                            fallback_rows.append([line.strip()])
                df_fallback = pd.DataFrame(fallback_rows, columns=["Extracted Text"])
                stitched_tables = [{
                    "table_id": 1,
                    "pages": list(range(1, total_pages + 1)),
                    "headers": ["Extracted Text"],
                    "rows": fallback_rows,
                    "dataframe": df_fallback
                }]

            if progress_callback:
                progress_callback(total_pages, total_pages, "Running data integrity & math validation...")

            # 4. Run Data Validation on each stitched table
            validation_reports: List[ValidationReport] = []
            for t_info in stitched_tables:
                df = t_info["dataframe"]
                v_rep = self.validator.validate_table(df, table_id=t_info["table_id"])
                validation_reports.append(v_rep)

            if progress_callback:
                progress_callback(total_pages, total_pages, "Generating styled Excel spreadsheet...")

            # 5. Export to Corporate-styled Excel Workbook
            doc_metadata = {
                "filename": os.path.basename(input_path),
                "total_pages": total_pages,
                "doc_type": ", ".join(sorted(set(page_types.values()))).title(),
                "timestamp": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            self.excel_writer.export_workbook(
                tables_data=stitched_tables,
                validation_reports=validation_reports,
                output_filepath=output_path,
                doc_metadata=doc_metadata
            )

            elapsed = time.time() - start_time
            return ProcessResult(
                success=True,
                source_path=input_path,
                output_excel_path=output_path,
                total_pages=total_pages,
                tables_data=stitched_tables,
                validation_reports=validation_reports,
                page_types=page_types,
                elapsed_seconds=elapsed
            )

        except Exception as e:
            elapsed = time.time() - start_time
            return ProcessResult(
                success=False,
                source_path=input_path,
                output_excel_path=output_path,
                total_pages=total_pages,
                tables_data=[],
                validation_reports=[],
                page_types=page_types,
                elapsed_seconds=elapsed,
                error_message=str(e)
            )

        finally:
            doc_fitz.close()
            if plumber_doc is not None:
                plumber_doc.close()
