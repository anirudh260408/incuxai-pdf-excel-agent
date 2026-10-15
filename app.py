"""
INCUXAI AI AGENT: Interactive Streamlit Web Application.
Provides a modern UI for uploading PDFs/images, viewing live extraction progress,
inspecting extracted tables, reviewing AI audit warnings, and downloading styled Excel workbooks.
"""

import os
import tempfile
import streamlit as st
import pandas as pd
import openpyxl
import pymupdf
from PIL import Image

from agent.pipeline import DocumentPipeline, ProcessResult

st.set_page_config(
    page_title="INCUXAI AI Agent | PDF to Excel",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1B365D;
        margin-bottom: 0px;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #555555;
        margin-bottom: 20px;
    }
    .metric-card {
        background-color: #F8F9FA;
        border: 1px solid #E9ECEF;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
    }
    .badge-pass {
        background-color: #D4EDDA;
        color: #155724;
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: bold;
    }
    .badge-error {
        background-color: #F8D7DA;
        color: #721C24;
        padding: 4px 10px;
        border-radius: 4px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


def get_pipeline():
    if "pipeline" not in st.session_state:
        st.session_state.pipeline = DocumentPipeline()
    return st.session_state.pipeline


def main():
    st.markdown('<div class="main-header">🚀 INCUXAI AI AGENT 🤖</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Autonomous PDF & Scanned Document to Excel Converter with OCR & Math Integrity Auditing</div>', unsafe_allow_html=True)

    # Sidebar: Controls & Sample Selector
    st.sidebar.header("📁 Document Selection")
    
    samples_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "samples")
    sample_options = {
        "Upload Custom Document": None,
        "Sample 1: Multi-Page Financial Statement (4 Pages)": os.path.join(samples_dir, "sample_1_financial_statement.pdf"),
        "Sample 2: Master Inventory Report (12 Columns)": os.path.join(samples_dir, "sample_2_inventory_order_report.pdf"),
        "Sample 3: Scanned Logistics Tax Invoice (OCR)": os.path.join(samples_dir, "sample_3_scanned_invoice.pdf"),
        "Sample 4: 50-Page Enterprise Stress Test": os.path.join(samples_dir, "stress_test_50_pages.pdf")
    }

    selected_mode = st.sidebar.selectbox("Choose Input Source:", list(sample_options.keys()))

    target_pdf_path = None
    original_filename = None

    if selected_mode == "Upload Custom Document":
        uploaded_file = st.sidebar.file_uploader(
            "Upload PDF or Scanned Document (up to 50 pages)",
            type=["pdf", "png", "jpg", "jpeg"]
        )
        if uploaded_file is not None:
            temp_dir = tempfile.mkdtemp()
            target_pdf_path = os.path.join(temp_dir, uploaded_file.name)
            with open(target_pdf_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            original_filename = uploaded_file.name
    else:
        sample_path = sample_options[selected_mode]
        if os.path.exists(sample_path):
            target_pdf_path = sample_path
            original_filename = os.path.basename(sample_path)
        else:
            st.sidebar.error("Sample document not found on disk. Run `python samples/generate_samples.py` first.")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚙️ Agent Engine Features")
    st.sidebar.markdown("""
    - ✅ **50-Page Streaming Architecture**
    - ✅ **10+ Wide Column Alignment**
    - ✅ **Tesseract Optical Character Recognition**
    - ✅ **Multi-Page Table Stitcher**
    - ✅ **Arithmetic & Ledger Validator**
    - ✅ **Interactive Excel Comment Highlights**
    """)

    # Main Processing Section
    if target_pdf_path:
        col_info1, col_info2 = st.columns([3, 1])
        with col_info1:
            st.info(f"📄 Selected Document: **{original_filename}**")
        with col_info2:
            process_btn = st.button("⚡ Convert with AI Agent", type="primary", use_container_width=True)

        if process_btn or ("last_processed" in st.session_state and st.session_state.last_processed == target_pdf_path):
            st.session_state.last_processed = target_pdf_path

            progress_bar = st.progress(0)
            status_text = st.empty()

            pipeline = get_pipeline()

            def update_progress(cur, total, msg):
                pct = int((cur / max(total, 1)) * 100)
                progress_bar.progress(pct)
                status_text.text(f"⏳ {msg} ({pct}%)")

            # Execute pipeline
            out_excel = os.path.join(tempfile.gettempdir(), f"{os.path.splitext(original_filename)[0]}_converted.xlsx")
            res: ProcessResult = pipeline.process_document(
                target_pdf_path,
                output_path=out_excel,
                progress_callback=update_progress
            )

            progress_bar.progress(100)
            status_text.text("✅ Processing Complete!")

            if res.success:
                st.success(f"Successfully converted **{original_filename}** in **{res.elapsed_seconds}s**!")

                # KPI Metric Cards
                k1, k2, k3, k4, k5 = st.columns(5)
                k1.metric("Total Pages", res.total_pages)
                k2.metric("Tables Found", res.total_tables)
                k3.metric("Rows Extracted", f"{res.total_rows:,}")
                k4.metric("Integrity Score", f"{res.overall_integrity_score}%")
                k5.metric("Audit Findings", f"{res.total_errors} Err / {res.total_warnings} Warn")

                # Action Bar: Download Button
                with open(res.output_excel_path, "rb") as f_excel:
                    excel_bytes = f_excel.read()

                st.download_button(
                    label="📥 Download Formatted Excel Workbook (.xlsx)",
                    data=excel_bytes,
                    file_name=f"{os.path.splitext(original_filename)[0]}_clean.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                    type="primary"
                )

                st.markdown("---")

                # Tabs: Extracted Data, AI Audit Register, Document Preview
                tab_data, tab_audit, tab_preview = st.tabs([
                    "📊 Extracted Tables",
                    "🛡️ AI Audit & Data Integrity Register",
                    "👁️ Document Page Preview"
                ])

                with tab_data:
                    for t_idx, t_data in enumerate(res.tables_data):
                        st.subheader(f"Table {t_data['table_id']} (Pages: {', '.join(map(str, t_data['pages']))})")
                        df = t_data["dataframe"]
                        st.caption(f"Shape: {df.shape[0]} rows × {df.shape[1]} columns")
                        st.dataframe(df, use_container_width=True, height=450)

                with tab_audit:
                    st.subheader("Data Integrity, Arithmetic & Alignment Audit")
                    all_findings = []
                    for rep in res.validation_reports:
                        for f in rep.findings:
                            all_findings.append({
                                "Table": f"Table {rep.table_id}",
                                "Row": f.row_idx + 1 if f.row_idx >= 0 else "All Rows",
                                "Column": f.col_name,
                                "Severity": f.severity,
                                "Finding Type": f.finding_type,
                                "Reported Value": f.actual_value or "-",
                                "Expected Value": f.expected_value or "-",
                                "Auditor Findings / Action Required": f.message
                            })

                    if all_findings:
                        df_findings = pd.DataFrame(all_findings)
                        st.dataframe(
                            df_findings,
                            use_container_width=True,
                            column_config={
                                "Severity": st.column_config.TextColumn(
                                    "Severity",
                                    help="ERROR indicates math or structural failure; WARNING indicates alignment or sparsity issue"
                                )
                            }
                        )
                        st.info("💡 Note: All flagged cells in the downloaded Excel workbook are highlighted in color with hover comments explaining the exact audit calculation.")
                    else:
                        st.success("🎉 No discrepancies or arithmetic errors detected! 100% Data Integrity Verified.")

                with tab_preview:
                    st.subheader("Source Document Page Inspection")
                    fitz_doc = pymupdf.open(target_pdf_path)
                    preview_page = st.slider("Select Page to View", 1, len(fitz_doc), 1)
                    p = fitz_doc[preview_page - 1]
                    pix = p.get_pixmap(dpi=150)
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    st.image(img, caption=f"Page {preview_page} of {len(fitz_doc)} (Classified as: {res.page_types.get(preview_page, 'N/A')})", width=650)
                    fitz_doc.close()

            else:
                st.error(f"Extraction failed: {res.error_message}")
    else:
        st.info("👈 Please select a sample document or upload a PDF/scanned document from the sidebar to begin.")


if __name__ == "__main__":
    main()
