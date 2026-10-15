"""
Professional Excel Writer with OpenPyXL.
Generates corporate-grade Excel workbooks with:
- Executive Summary & Audit Dashboard sheet
- Styled table sheets (dark navy headers, zebra striping, auto-adjusted column widths)
- Cell-level conditional error highlighting (soft red/yellow fills)
- Interactive hover tooltips (Excel Comments) detailing detected math errors & misalignments
- Accounting double-underlines for totals
"""

from typing import List, Dict, Any, Optional
import os
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.comments import Comment
import pandas as pd

from .validator import ValidationReport, ValidationFinding


class ProfessionalExcelWriter:
    """Enterprise-grade Excel generator and visual audit highlighter."""

    def __init__(self):
        # Color Palette
        self.NAVY_HEADER_FILL = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
        self.HEADER_FONT = Font(name="Segoe UI", size=11, bold=True, color="FFFFFF")
        
        self.ZEBRA_FILL = PatternFill(start_color="F7F9FC", end_color="F7F9FC", fill_type="solid")
        self.WHITE_FILL = PatternFill(start_color="FFFFFF", end_color="FFFFFF", fill_type="solid")
        
        # Error & Warning Fills
        self.ERROR_FILL = PatternFill(start_color="FFD6D6", end_color="FFD6D6", fill_type="solid")
        self.ERROR_FONT = Font(name="Segoe UI", size=10, bold=True, color="900000")
        
        self.WARNING_FILL = PatternFill(start_color="FFF3CD", end_color="FFF3CD", fill_type="solid")
        self.WARNING_FONT = Font(name="Segoe UI", size=10, color="856404")

        # KPI Fills
        self.KPI_BG = PatternFill(start_color="EBF3FB", end_color="EBF3FB", fill_type="solid")
        self.KPI_FONT = Font(name="Segoe UI", size=12, bold=True, color="1B365D")

        # Borders
        self.THIN_BORDER_SIDE = Side(border_style="thin", color="D3D9DE")
        self.CELL_BORDER = Border(
            left=self.THIN_BORDER_SIDE,
            right=self.THIN_BORDER_SIDE,
            top=self.THIN_BORDER_SIDE,
            bottom=self.THIN_BORDER_SIDE
        )
        self.TOTAL_BORDER = Border(
            top=Side(border_style="thin", color="1B365D"),
            bottom=Side(border_style="double", color="1B365D")
        )

        # Alignments
        self.ALIGN_LEFT = Alignment(horizontal="left", vertical="center")
        self.ALIGN_RIGHT = Alignment(horizontal="right", vertical="center")
        self.ALIGN_CENTER = Alignment(horizontal="center", vertical="center")

    def export_workbook(
        self,
        tables_data: List[Dict[str, Any]],
        validation_reports: List[ValidationReport],
        output_filepath: str,
        doc_metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build and save the formatted multi-sheet Excel file.
        """
        wb = openpyxl.Workbook()
        wb.remove(wb.active)  # Remove default blank sheet

        # 1. Add Executive Audit Summary Sheet
        self._create_summary_sheet(wb, tables_data, validation_reports, doc_metadata)

        # 2. Add each extracted table as a distinct formatted sheet
        for idx, t_info in enumerate(tables_data):
            df = t_info["dataframe"]
            v_rep = validation_reports[idx] if idx < len(validation_reports) else None
            sheet_title = f"Table {t_info['table_id']}"
            if len(tables_data) == 1 and doc_metadata and "title" in doc_metadata:
                sheet_title = doc_metadata["title"][:28]

            self._create_table_sheet(wb, df, sheet_title, t_info, v_rep)

        os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
        wb.save(output_filepath)
        return output_filepath

    def _create_summary_sheet(
        self,
        wb: openpyxl.Workbook,
        tables_data: List[Dict[str, Any]],
        validation_reports: List[ValidationReport],
        doc_metadata: Optional[Dict[str, Any]]
    ):
        """Create executive validation audit dashboard."""
        ws = wb.create_sheet(title="Audit & Validation Summary")
        ws.views.sheetView[0].showGridLines = True

        # Document Header
        ws.merge_cells("A1:G1")
        title_cell = ws["A1"]
        title_cell.value = "INCUXAI AI AGENT: DOCUMENT EXTRACTION & VALIDATION REPORT"
        title_cell.font = Font(name="Segoe UI", size=14, bold=True, color="FFFFFF")
        title_cell.fill = self.NAVY_HEADER_FILL
        title_cell.alignment = self.ALIGN_CENTER
        ws.row_dimensions[1].height = 35

        # Metadata Row
        meta = doc_metadata or {}
        ws["A3"] = "Source File:"
        ws["B3"] = meta.get("filename", "Input Document")
        ws["A4"] = "Pages Processed:"
        ws["B4"] = meta.get("total_pages", "N/A")
        ws["D3"] = "Document Type:"
        ws["E3"] = meta.get("doc_type", "Digital / OCR Hybrid")
        ws["D4"] = "Extraction Date:"
        ws["E4"] = meta.get("timestamp", pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"))

        for r in [3, 4]:
            ws[f"A{r}"].font = Font(name="Segoe UI", size=10, bold=True, color="555555")
            ws[f"D{r}"].font = Font(name="Segoe UI", size=10, bold=True, color="555555")
            ws[f"B{r}"].font = Font(name="Segoe UI", size=10, bold=True)
            ws[f"E{r}"].font = Font(name="Segoe UI", size=10)

        # KPI Summary Cards
        total_rows = sum(len(t["dataframe"]) for t in tables_data)
        total_tables = len(tables_data)
        total_errors = sum(v.errors_count for v in validation_reports)
        total_warnings = sum(v.warnings_count for v in validation_reports)
        avg_score = sum(v.integrity_score for v in validation_reports) / max(len(validation_reports), 1)

        kpis = [
            ("TOTAL TABLES", str(total_tables), "B6:B7"),
            ("ROWS EXTRACTED", f"{total_rows:,}", "C6:C7"),
            ("INTEGRITY SCORE", f"{round(avg_score, 1)}%", "D6:D7"),
            ("CRITICAL ERRORS", str(total_errors), "E6:E7"),
            ("AUDIT WARNINGS", str(total_warnings), "F6:F7"),
        ]

        for label, val, cell_range in kpis:
            col_letter = cell_range[0]
            ws[f"{col_letter}6"] = label
            ws[f"{col_letter}6"].font = Font(name="Segoe UI", size=9, bold=True, color="777777")
            ws[f"{col_letter}6"].alignment = self.ALIGN_CENTER

            ws[f"{col_letter}7"] = val
            val_color = "900000" if label == "CRITICAL ERRORS" and total_errors > 0 else "1B365D"
            if label == "INTEGRITY SCORE" and avg_score >= 95:
                val_color = "007A33"
            ws[f"{col_letter}7"].font = Font(name="Segoe UI", size=14, bold=True, color=val_color)
            ws[f"{col_letter}7"].alignment = self.ALIGN_CENTER
            ws[f"{col_letter}7"].fill = self.KPI_BG

        # Audit Findings Table
        ws["A9"] = "AUDIT FINDINGS & DISCREPANCY REGISTER"
        ws["A9"].font = Font(name="Segoe UI", size=12, bold=True, color="1B365D")

        headers = ["Table #", "Row #", "Column Name", "Finding Type", "Severity", "Reported Value", "Expected Value", "Auditor Findings / Action Required"]
        for col_idx, h in enumerate(headers, 1):
            c = ws.cell(row=10, column=col_idx, value=h)
            c.font = self.HEADER_FONT
            c.fill = self.NAVY_HEADER_FILL
            c.alignment = self.ALIGN_CENTER
        ws.row_dimensions[10].height = 24

        curr_row = 11
        for idx, v_rep in enumerate(validation_reports):
            t_id = v_rep.table_id
            for f in v_rep.findings:
                ws.cell(row=curr_row, column=1, value=f"Table {t_id}").alignment = self.ALIGN_CENTER
                ws.cell(row=curr_row, column=2, value=f.row_idx + 1 if f.row_idx >= 0 else "All").alignment = self.ALIGN_CENTER
                ws.cell(row=curr_row, column=3, value=f.col_name).alignment = self.ALIGN_LEFT
                ws.cell(row=curr_row, column=4, value=f.finding_type).alignment = self.ALIGN_LEFT

                # Severity badge
                sev_cell = ws.cell(row=curr_row, column=5, value=f.severity)
                sev_cell.alignment = self.ALIGN_CENTER
                if f.severity == "ERROR":
                    sev_cell.fill = self.ERROR_FILL
                    sev_cell.font = self.ERROR_FONT
                else:
                    sev_cell.fill = self.WARNING_FILL
                    sev_cell.font = self.WARNING_FONT

                ws.cell(row=curr_row, column=6, value=f.actual_value or "-").alignment = self.ALIGN_RIGHT
                ws.cell(row=curr_row, column=7, value=f.expected_value or "-").alignment = self.ALIGN_RIGHT
                ws.cell(row=curr_row, column=8, value=f.message).alignment = self.ALIGN_LEFT

                for c_i in range(1, 9):
                    ws.cell(row=curr_row, column=c_i).border = self.CELL_BORDER

                curr_row += 1

        if curr_row == 11:
            ws.cell(row=11, column=1, value="No discrepancies or math errors detected! 100% Data Integrity Verified.")
            ws.merge_cells("A11:H11")
            ws["A11"].font = Font(name="Segoe UI", size=11, bold=True, color="007A33")
            ws["A11"].alignment = self.ALIGN_CENTER
            ws.row_dimensions[11].height = 22

        # Auto adjust column widths
        self._auto_fit_columns(ws, min_width=12)

    def _create_table_sheet(
        self,
        wb: openpyxl.Workbook,
        df: pd.DataFrame,
        sheet_title: str,
        table_info: Dict[str, Any],
        v_report: Optional[ValidationReport]
    ):
        """Create styled data table worksheet with visual error highlights and hover comments."""
        # Ensure sheet title is unique and <= 31 chars
        valid_title = sheet_title[:30].replace("/", "-").replace("\\", "-").replace("?", "")
        ws = wb.create_sheet(title=valid_title)
        ws.views.sheetView[0].showGridLines = True

        # Pre-index findings for fast lookup: (row_idx, col_name) -> finding
        finding_map: Dict[tuple, ValidationFinding] = {}
        if v_report:
            for f in v_report.findings:
                if f.row_idx >= 0:
                    finding_map[(f.row_idx, str(f.col_name))] = f

        # Write Headers
        headers = list(df.columns)
        for col_idx, col_name in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col_idx, value=col_name)
            cell.font = self.HEADER_FONT
            cell.fill = self.NAVY_HEADER_FILL
            cell.alignment = self.ALIGN_CENTER
            cell.border = self.CELL_BORDER
        ws.row_dimensions[1].height = 28

        # Write Data Rows
        for r_idx, row_series in df.iterrows():
            excel_row = r_idx + 2
            is_zebra = (r_idx % 2 == 1)
            row_fill = self.ZEBRA_FILL if is_zebra else self.WHITE_FILL

            is_total_row = any("total" in str(x).lower() for x in row_series.values[:2])

            for c_idx, col_name in enumerate(headers, 1):
                val = row_series[col_name]
                cell = ws.cell(row=excel_row, column=c_idx)

                # Format and convert numeric if possible
                num_val = None
                s_val = str(val).strip() if val is not None else ""
                
                # Check numeric conversion
                try:
                    cleaned_s = s_val.replace("$", "").replace("₹", "").replace(",", "").replace("%", "").strip()
                    if cleaned_s and not is_total_row:
                        num_val = float(cleaned_s)
                        if num_val.is_integer():
                            cell.value = int(num_val)
                            cell.number_format = '#,##0'
                        else:
                            cell.value = num_val
                            cell.number_format = '#,##0.00'
                    else:
                        cell.value = s_val
                except Exception:
                    cell.value = s_val

                # Alignments
                if isinstance(cell.value, (int, float)):
                    cell.alignment = self.ALIGN_RIGHT
                elif len(s_val) <= 12 and any(char.isdigit() for char in s_val):
                    cell.alignment = self.ALIGN_CENTER
                else:
                    cell.alignment = self.ALIGN_LEFT

                # Base Styling
                cell.font = Font(name="Segoe UI", size=10, bold=is_total_row)
                cell.fill = row_fill
                cell.border = self.TOTAL_BORDER if is_total_row else self.CELL_BORDER

                # Check for Validation Error Highlighting
                key = (r_idx, str(col_name))
                if key in finding_map:
                    f = finding_map[key]
                    if f.severity == "ERROR":
                        cell.fill = self.ERROR_FILL
                        cell.font = self.ERROR_FONT
                    else:
                        cell.fill = self.WARNING_FILL
                        cell.font = self.WARNING_FONT

                    # Attach hover tooltip comment
                    comment_text = f"[AI Audit Alert]\n{f.message}"
                    cell.comment = Comment(comment_text, "INCUXAI AI Agent")

            ws.row_dimensions[excel_row].height = 20

        # Auto adjust column widths
        self._auto_fit_columns(ws, min_width=12)

    def _auto_fit_columns(self, ws: openpyxl.worksheet.worksheet.Worksheet, min_width: int = 12):
        """Auto fit all columns with safety margin so text is never truncated."""
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val = cell.value
                if val:
                    # If multi-line, take longest line
                    lines = str(val).split("\n")
                    line_len = max(len(l) for l in lines)
                    if line_len > max_len:
                        max_len = line_len
            ws.column_dimensions[col_letter].width = max(max_len + 4, min_width)
