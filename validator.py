"""
Data Validation and Error Detection Engine.
Validates table integrity, detects misaligned columns, checks arithmetic totals,
verifies row-level calculations (Qty * Price = Total), and checks ledger running balances.
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import re
import pandas as pd
import numpy as np


@dataclass
class ValidationFinding:
    row_idx: int  # 0-indexed data row, -1 for column-wide
    col_name: str
    finding_type: str  # "MATH_ROW_MISMATCH", "TOTAL_MISMATCH", "MISALIGNED_DATA", "EMPTY_COLUMN", "LEDGER_DRIFT"
    message: str
    severity: str  # "ERROR", "WARNING", "INFO"
    actual_value: Optional[str] = None
    expected_value: Optional[str] = None


@dataclass
class ValidationReport:
    table_id: int
    total_rows: int
    total_cols: int
    total_cells: int
    integrity_score: float
    errors_count: int
    warnings_count: int
    passed: bool
    findings: List[ValidationFinding] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_id": self.table_id,
            "total_rows": self.total_rows,
            "total_cols": self.total_cols,
            "total_cells": self.total_cells,
            "integrity_score": round(self.integrity_score, 2),
            "errors_count": self.errors_count,
            "warnings_count": self.warnings_count,
            "passed": self.passed,
            "findings_count": len(self.findings),
        }


class DataValidator:
    """Comprehensive data integrity, alignment, and arithmetic verification engine."""

    def __init__(self, tolerance: float = 0.05):
        self.tolerance = tolerance

    @staticmethod
    def parse_numeric(val: Any) -> Optional[float]:
        """Parse clean numeric float from string with currencies, commas, or parentheses."""
        if val is None or pd.isna(val):
            return None
        s = str(val).strip()
        if not s:
            return None

        # Parentheses indicating negative: (100.50) -> -100.50
        is_neg = False
        if s.startswith('(') and s.endswith(')'):
            is_neg = True
            s = s[1:-1].strip()

        # Remove currency symbols, commas, spaces, percentages
        s_clean = re.sub(r'[\$,₹€£%\s]', '', s)
        try:
            num = float(s_clean)
            return -num if is_neg else num
        except ValueError:
            return None

    @staticmethod
    def is_date_string(val: str) -> bool:
        """Check if string looks like a standard date."""
        if not val or len(val) < 6:
            return False
        patterns = [
            r'^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}$',
            r'^\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}$',
            r'^\d{1,2}\s+[A-Za-z]{3,9}\s+\d{2,4}$',
        ]
        return any(re.match(p, val.strip()) for p in patterns)

    def validate_table(self, df: pd.DataFrame, table_id: int = 1) -> ValidationReport:
        """Run all validation suites on a table DataFrame."""
        findings: List[ValidationFinding] = []
        total_rows = len(df)
        total_cols = len(df.columns)
        total_cells = max(1, total_rows * total_cols)

        if df.empty:
            return ValidationReport(
                table_id=table_id,
                total_rows=0,
                total_cols=0,
                total_cells=0,
                integrity_score=100.0,
                errors_count=0,
                warnings_count=0,
                passed=True,
                findings=[]
            )

        # 1. Audit Empty / Sparse Columns
        self._audit_empty_columns(df, findings)

        # 2. Audit Column Alignment & Type Anomalies
        self._audit_column_alignments(df, findings)

        # 3. Audit Row Arithmetic (e.g. Qty * Price = Total)
        self._audit_row_math(df, findings)

        # 4. Audit Column Totals (Sum of rows vs stated Total row)
        self._audit_column_totals(df, findings)

        # 5. Audit Ledger Running Balance (Debit, Credit, Balance)
        self._audit_ledger_balance(df, findings)

        errors_count = sum(1 for f in findings if f.severity == "ERROR")
        warnings_count = sum(1 for f in findings if f.severity == "WARNING")

        # Integrity Score Calculation
        # Base 100, deduction per error / warning relative to cell count
        penalty = (errors_count * 5.0) + (warnings_count * 1.5)
        integrity_score = max(0.0, min(100.0, 100.0 - (penalty / max(total_rows, 5) * 10.0)))
        passed = (errors_count == 0)

        return ValidationReport(
            table_id=table_id,
            total_rows=total_rows,
            total_cols=total_cols,
            total_cells=total_cells,
            integrity_score=integrity_score,
            errors_count=errors_count,
            warnings_count=warnings_count,
            passed=passed,
            findings=findings
        )

    def _audit_empty_columns(self, df: pd.DataFrame, findings: List[ValidationFinding]):
        """Detect completely empty or extremely sparse columns."""
        for col in df.columns:
            non_empty = df[col].astype(str).str.strip().replace('', np.nan).dropna()
            fill_ratio = len(non_empty) / max(len(df), 1)
            if fill_ratio == 0:
                findings.append(ValidationFinding(
                    row_idx=-1,
                    col_name=str(col),
                    finding_type="EMPTY_COLUMN",
                    message=f"Column '{col}' is completely empty (100% blank).",
                    severity="WARNING",
                    actual_value="0% populated",
                    expected_value=">50% populated"
                ))
            elif fill_ratio < 0.15 and len(df) > 5:
                findings.append(ValidationFinding(
                    row_idx=-1,
                    col_name=str(col),
                    finding_type="SPARSE_COLUMN",
                    message=f"Column '{col}' is highly sparse ({round(fill_ratio*100, 1)}% populated).",
                    severity="INFO",
                    actual_value=f"{round(fill_ratio*100, 1)}%",
                    expected_value=">50%"
                ))

    def _audit_column_alignments(self, df: pd.DataFrame, findings: List[ValidationFinding]):
        """Audit whether data types within each column are uniform or if cells are shifted."""
        for col in df.columns:
            series = df[col].astype(str).str.strip()
            # Non-empty values
            vals = [v for v in series if v and v != "nan" and v != "None"]
            if len(vals) < 4:
                continue

            num_count = sum(1 for v in vals if self.parse_numeric(v) is not None)
            date_count = sum(1 for v in vals if self.is_date_string(v))
            total_v = len(vals)

            # Predominantly numeric column (>80% numeric)
            if (num_count / total_v) >= 0.8:
                for r_idx, val in enumerate(series):
                    if val and val != "nan" and val != "None":
                        # If row is a summary total row, skip text labels like "Total"
                        is_summary_row = any("total" in str(x).lower() for x in df.iloc[r_idx].values[:2])
                        if is_summary_row:
                            continue
                        if self.parse_numeric(val) is None:
                            findings.append(ValidationFinding(
                                row_idx=r_idx,
                                col_name=str(col),
                                finding_type="MISALIGNED_DATA",
                                message=f"Expected numeric value in column '{col}', but found text: '{val}'. Possible cell shift.",
                                severity="WARNING",
                                actual_value=val,
                                expected_value="Numeric Value"
                            ))

            # Predominantly date column (>80% date)
            elif (date_count / total_v) >= 0.8:
                for r_idx, val in enumerate(series):
                    if val and val != "nan" and val != "None":
                        is_summary_row = any("total" in str(x).lower() for x in df.iloc[r_idx].values[:2])
                        if is_summary_row:
                            continue
                        if not self.is_date_string(val):
                            findings.append(ValidationFinding(
                                row_idx=r_idx,
                                col_name=str(col),
                                finding_type="MISALIGNED_DATA",
                                message=f"Expected date in column '{col}', but found: '{val}'.",
                                severity="WARNING",
                                actual_value=val,
                                expected_value="Date Format"
                            ))

    def _audit_row_math(self, df: pd.DataFrame, findings: List[ValidationFinding]):
        """Check row-level calculations: Quantity * Unit Price == Total / Amount."""
        cols_lower = {str(c).lower().strip(): c for c in df.columns}

        # Identify Qty column
        qty_col = None
        for k in ["qty", "quantity", "units", "units in stock", "units on order", "quantity ordered"]:
            if k in cols_lower:
                qty_col = cols_lower[k]
                break

        # Identify Price column
        price_col = None
        for k in ["price", "unit price", "rate", "cost", "unit cost ($)", "retail price ($)", "unit rate"]:
            if k in cols_lower:
                price_col = cols_lower[k]
                break

        # Identify Total column
        total_col = None
        for k in ["total", "amount", "total value ($)", "total amount", "line total", "total ($)", "ext price"]:
            if k in cols_lower:
                total_col = cols_lower[k]
                break

        if qty_col and price_col and total_col and (qty_col != total_col) and (price_col != total_col):
            for r_idx in range(len(df)):
                # Skip summary rows
                row_str = " ".join([str(x).lower() for x in df.iloc[r_idx].values[:3]])
                if "total" in row_str or "summary" in row_str:
                    continue

                q_val = self.parse_numeric(df.at[r_idx, qty_col])
                p_val = self.parse_numeric(df.at[r_idx, price_col])
                t_val = self.parse_numeric(df.at[r_idx, total_col])

                if q_val is not None and p_val is not None and t_val is not None:
                    expected_total = q_val * p_val
                    # Also consider if there's a discount or tax column
                    diff = abs(expected_total - t_val)
                    if diff > max(self.tolerance, 0.05 * max(abs(t_val), 1.0)):
                        findings.append(ValidationFinding(
                            row_idx=r_idx,
                            col_name=str(total_col),
                            finding_type="MATH_ROW_MISMATCH",
                            message=f"Row {r_idx+1} Math Error: {qty_col} ({q_val}) * {price_col} ({p_val}) = {round(expected_total, 2)}, but found {t_val} (Discrepancy: {round(t_val - expected_total, 2)})",
                            severity="ERROR",
                            actual_value=str(t_val),
                            expected_value=str(round(expected_total, 2))
                        ))

    def _audit_column_totals(self, df: pd.DataFrame, findings: List[ValidationFinding]):
        """Detect explicit 'Total' or 'Grand Total' rows and verify sum against rows above."""
        total_row_indices = []
        for r_idx in range(len(df)):
            first_cells = " ".join([str(x).lower() for x in df.iloc[r_idx].values[:2]])
            if re.search(r'\b(total|grand\s+total|subtotal|sub-total)\b', first_cells):
                total_row_indices.append(r_idx)

        for t_idx in total_row_indices:
            # Check numeric columns
            for col in df.columns:
                stated_total = self.parse_numeric(df.at[t_idx, col])
                if stated_total is not None and stated_total != 0:
                    # Calculate sum of rows above t_idx (or since previous total)
                    prev_start = 0
                    for prev_t in total_row_indices:
                        if prev_t < t_idx:
                            prev_start = prev_t + 1

                    row_vals = [
                        self.parse_numeric(df.at[r, col])
                        for r in range(prev_start, t_idx)
                    ]
                    clean_vals = [v for v in row_vals if v is not None]

                    if clean_vals and len(clean_vals) >= 2:
                        calc_sum = sum(clean_vals)
                        diff = abs(calc_sum - stated_total)
                        if diff > max(self.tolerance, 0.01 * max(abs(stated_total), 1.0)):
                            findings.append(ValidationFinding(
                                row_idx=t_idx,
                                col_name=str(col),
                                finding_type="TOTAL_MISMATCH",
                                message=f"Column Total Discrepancy on '{col}': Sum of rows is {round(calc_sum, 2)}, but reported total is {stated_total} (Difference: {round(stated_total - calc_sum, 2)})",
                                severity="ERROR",
                                actual_value=str(stated_total),
                                expected_value=str(round(calc_sum, 2))
                            ))

    def _audit_ledger_balance(self, df: pd.DataFrame, findings: List[ValidationFinding]):
        """Verify running balance in bank statements / ledgers: Balance[i] == Balance[i-1] + Credit - Debit."""
        cols_lower = {str(c).lower().strip(): c for c in df.columns}

        debit_col = None
        for k in ["debit", "debit (inr)", "withdrawal", "withdrawals", "debit amount", "paid out"]:
            if k in cols_lower:
                debit_col = cols_lower[k]
                break

        credit_col = None
        for k in ["credit", "credit (inr)", "deposit", "deposits", "credit amount", "paid in"]:
            if k in cols_lower:
                credit_col = cols_lower[k]
                break

        balance_col = None
        for k in ["balance", "balance (inr)", "closing balance", "running balance", "net balance"]:
            if k in cols_lower:
                balance_col = cols_lower[k]
                break

        if balance_col and (debit_col or credit_col):
            prev_balance: Optional[float] = None
            for r_idx in range(len(df)):
                row_str = " ".join([str(x).lower() for x in df.iloc[r_idx].values[:2]])
                if "total" in row_str:
                    continue

                curr_bal = self.parse_numeric(df.at[r_idx, balance_col])
                deb = self.parse_numeric(df.at[r_idx, debit_col]) if debit_col else 0.0
                crd = self.parse_numeric(df.at[r_idx, credit_col]) if credit_col else 0.0

                deb = deb if deb is not None else 0.0
                crd = crd if crd is not None else 0.0

                if curr_bal is not None:
                    if prev_balance is not None:
                        # Standard ledger: new_bal = prev_bal + credit - debit
                        expected_bal = prev_balance + crd - deb
                        diff = abs(expected_bal - curr_bal)
                        if diff > 0.05:
                            findings.append(ValidationFinding(
                                row_idx=r_idx,
                                col_name=str(balance_col),
                                finding_type="LEDGER_DRIFT",
                                message=f"Row {r_idx+1} Running Balance Mismatch: Prev ({round(prev_balance, 2)}) + Credit ({crd}) - Debit ({deb}) = {round(expected_bal, 2)}, but found {curr_bal}",
                                severity="ERROR",
                                actual_value=str(curr_bal),
                                expected_value=str(round(expected_bal, 2))
                            ))
                    prev_balance = curr_bal
