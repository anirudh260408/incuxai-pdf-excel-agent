"""
INCUXAI AI AGENT: Command-Line Interface.
Usage:
    python main.py --input samples/sample_1_financial_statement.pdf
    python main.py --batch samples/ --output-dir samples/converted/
"""

import argparse
import os
import sys
import glob
from agent.pipeline import DocumentPipeline


def print_banner():
    banner = """
================================================================================
  🚀 INCUXAI AI AGENT: PDF & SCANNED DOCUMENT TO EXCEL CONVERTER 🤖
  Automatic Table Extraction | Multi-Page Stitching | AI Data Integrity Auditor
================================================================================
"""
    print(banner)


def process_single_file(pipeline: DocumentPipeline, input_file: str, output_file: str = None):
    print(f"\n📂 Processing: {os.path.basename(input_file)}")
    print(f"   Path: {input_file}")

    def progress_callback(cur, total, msg):
        percent = int((cur / max(total, 1)) * 100)
        bar = "█" * (percent // 5) + "-" * (20 - (percent // 5))
        sys.stdout.write(f"\r   [{bar}] {percent}% | {msg}")
        sys.stdout.flush()

    res = pipeline.process_document(input_file, output_path=output_file, progress_callback=progress_callback)
    print("\n")

    if res.success:
        print("   ✅ CONVERSION SUCCESSFUL!")
        print(f"   📊 Excel File: {res.output_excel_path}")
        print(f"   📄 Pages: {res.total_pages} | 📋 Tables: {res.total_tables} | 🔢 Rows Extracted: {res.total_rows}")
        print(f"   🛡️ Data Integrity Score: {res.overall_integrity_score}%")
        print(f"   ⚠️ Discrepancies Detected: {res.total_errors} Critical Errors, {res.total_warnings} Warnings")
        print(f"   ⏱️ Processing Time: {res.elapsed_seconds}s")

        if res.total_errors > 0 or res.total_warnings > 0:
            print("\n   🔍 AUDIT FINDINGS (Highlighted in Excel with Hover Tooltips):")
            for rep in res.validation_reports:
                for f in rep.findings:
                    badge = "❌ [ERROR]" if f.severity == "ERROR" else "⚠️ [WARNING]"
                    row_info = f"Row {f.row_idx + 1}" if f.row_idx >= 0 else "Column-wide"
                    print(f"      {badge} {row_info} ({f.col_name}): {f.message}")
    else:
        print(f"   ❌ CONVERSION FAILED: {res.error_message}")

    return res


def main():
    print_banner()
    parser = argparse.ArgumentParser(description="INCUXAI AI Document-to-Excel Agent")
    parser.add_argument("--input", "-i", type=str, help="Path to input PDF or image file")
    parser.add_argument("--output", "-o", type=str, default=None, help="Path to output Excel file (.xlsx)")
    parser.add_argument("--batch", "-b", type=str, default=None, help="Directory containing PDF files for batch processing")
    parser.add_argument("--output-dir", "-d", type=str, default=None, help="Directory to save converted Excel files")

    args = parser.parse_args()

    pipeline = DocumentPipeline()

    if args.batch:
        batch_dir = os.path.abspath(args.batch)
        out_dir = os.path.abspath(args.output_dir) if args.output_dir else batch_dir
        os.makedirs(out_dir, exist_ok=True)

        pdf_files = sorted(glob.glob(os.path.join(batch_dir, "*.pdf")))
        if not pdf_files:
            print(f"No PDF files found in directory: {batch_dir}")
            sys.exit(1)

        print(f"Found {len(pdf_files)} PDF file(s) for batch processing.")
        results = []
        for pdf_path in pdf_files:
            base_name = os.path.splitext(os.path.basename(pdf_path))[0]
            out_excel = os.path.join(out_dir, f"{base_name}.xlsx")
            r = process_single_file(pipeline, pdf_path, out_excel)
            results.append(r)

        print("\n" + "=" * 80)
        print("✨ BATCH CONVERSION SUMMARY")
        print("=" * 80)
        for r in results:
            status = "✅ PASS" if r.success else "❌ FAIL"
            print(f"{status} | {os.path.basename(r.source_path):<35} | {r.total_rows:>4} rows | Score: {r.overall_integrity_score:>5}% | {r.elapsed_seconds:>4}s")
        print("=" * 80)

    elif args.input:
        process_single_file(pipeline, args.input, args.output)
    else:
        # Default behavior: run on the 3 sample files and output to samples/converted
        samples_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples")
        out_dir = os.path.join(samples_dir, "converted")
        os.makedirs(out_dir, exist_ok=True)

        sample_pdfs = sorted([
            os.path.join(samples_dir, "sample_1_financial_statement.pdf"),
            os.path.join(samples_dir, "sample_2_inventory_order_report.pdf"),
            os.path.join(samples_dir, "sample_3_scanned_invoice.pdf"),
        ])

        print(f"No input specified. Automatically processing all 3 hackathon sample PDFs into {out_dir}...")
        for pdf_path in sample_pdfs:
            if os.path.exists(pdf_path):
                base_name = os.path.splitext(os.path.basename(pdf_path))[0]
                out_excel = os.path.join(out_dir, f"{base_name}.xlsx")
                process_single_file(pipeline, pdf_path, out_excel)


if __name__ == "__main__":
    main()
