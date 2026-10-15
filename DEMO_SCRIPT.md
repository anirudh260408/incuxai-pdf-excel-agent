# 🎬 INCUXAI AI AGENT: DEMO VIDEO SCRIPT & RECORDING GUIDE
**Target Duration:** 3 to 4 Minutes  
**Application:** INCUXAI AI Document-to-Excel Conversion & Audit Agent  
**Host / Presenter:** Solo / Team Participant  

---

## 🕒 Timestamped Video Outline

| Scene | Timestamp | Screen Focus | Key Talking Points |
| :---: | :---: | :--- | :--- |
| **1** | 0:00 – 0:30 | Presenter / Intro slide & Terminal/Browser | Welcome judges, state problem (hours lost on manual data entry), introduce INCUXAI AI Agent. |
| **2** | 0:30 – 1:00 | Streamlit UI Dashboard (`streamlit run app.py`) | Walk through user interface, upload zone, sample selector, feature list. |
| **3** | 1:00 – 1:45 | Converting Sample 1 (4-Page Banking Statement) | Show multi-page table stitching, automatic removal of repeated headers, sub-second speed. |
| **4** | 1:45 – 2:30 | Converting Sample 2 (12-Column Inventory Report) | Show wide table alignment (>10 columns), demonstrate AI detecting the intentional $250 arithmetic mismatch. |
| **5** | 2:30 – 3:15 | Converting Sample 3 (Scanned Tax Invoice) & Excel Inspection | Demonstrate Tesseract OCR on scanned document, open generated Excel file, show cell color highlights & hover comments. |
| **6** | 3:15 – 3:45 | 50-Page Stress Test in Terminal & Wrap-up | Run `python evaluation.py` to prove sub-3 second processing on 50 pages / 1,000 rows. Conclusion & thank you. |

---

## 🎙️ Detailed Spoken Script

### Scene 1: Introduction (0:00 – 0:30)
> *"Hello Incuxai judges and evaluators! Welcome to our submission for the INCUXAI AI Agent Development Challenge 2026.*  
> *Every day, companies lose hundreds of hours manually keying in transactions from bank statements, multi-page invoices, and inventory logs into Excel. Typos and missed rows can cost businesses thousands.*  
> *Today, we present our autonomous AI Agent: a system that converts complex digital PDFs and scanned documents into corporate-grade Excel workbooks in seconds, complete with automated arithmetic and data integrity validation."*

### Scene 2: UI & Architecture Overview (0:30 – 1:00)
> *(Screen: Show Streamlit Web Interface at `localhost:8501`)*  
> *"Our agent provides both a modular Python CLI and an interactive web interface. Behind the scenes, the agent features an intelligent router that automatically classifies whether a page is digital text or a scanned raster image, routes it through an optimized Tesseract OCR or pdfplumber extraction pipeline, stitches multi-page tables, and executes a full data audit."*

### Scene 3: Multi-Page Financial Statement Conversion (1:00 – 1:45)
> *(Action: Select 'Sample 1: Multi-Page Financial Statement' from sidebar and click 'Convert with AI Agent')*  
> *"Let's test Sample 1. This is a 4-page corporate banking ledger with 55 transactions spanning across multiple pages, with repeating page headers and running balance columns.*  
> *Watch as we click 'Convert'. In just 0.25 seconds, the agent processes all 4 pages, detects and removes repeated headers, stitches 56 rows into a single continuous ledger, and audits the running balances and period totals."*

### Scene 4: 12-Column Wide Table & Error Detection (1:45 – 2:30)
> *(Action: Select 'Sample 2: Master Inventory Report (12 Columns)' and click 'Convert')*  
> *"Requirement 2 asks for tables with 10+ columns. Here we have a 12-column supply chain report with dense numerical data, unit prices, discounts, and total valuations.*  
> *Notice our AI Audit Register tab: the agent detected an intentional math error on Row 12! Units in stock (40) times unit cost (\$22.00) equals \$880.00, but the source document listed \$1,130.00. The agent automatically flags the discrepancy and calculates the exact \$250 difference."*

### Scene 5: Scanned Document OCR & Excel Visual Inspection (2:30 – 3:15)
> *(Action: Select 'Sample 3: Scanned Logistics Tax Invoice', convert, then click 'Download Formatted Excel Workbook', open in Excel)*  
> *"Requirement 3 specifies reading scanned documents using OCR. Sample 3 is a pure 300 DPI raster scanned tax invoice with realistic scan artifacts.*  
> *Our OCR engine enhances image contrast, applies adaptive binarization, isolates the table from header metadata, and extracts all line items.*  
> *When we open the generated Excel file, notice the executive styling: dark navy headers, zebra striping, auto-fitted columns, and an executive Audit Summary tab. If we hover over flagged cells, an interactive Excel comment pops up with the exact audit reasoning!"*

### Scene 6: 50-Page Stress Test & Conclusion (3:15 – 3:45)
> *(Action: Switch to terminal and run `python evaluation.py`)*  
> *"Finally, to prove Requirement 1—handling PDFs of up to 50 pages—we run our automated evaluation suite. The agent processes a 50-page enterprise audit document containing 1,000 table rows in just 2.94 seconds—that's under 0.06 seconds per page with 100% column precision.*  
> *Our project is fully open-source, reproducible, and ready for deployment. Thank you for your consideration, and we look forward to the results!"*

---

## 🛠️ Recording Checklist for Presenters
- [ ] Open OBS Studio, QuickTime, or Loom with 1080p resolution and clear microphone audio.
- [ ] Have the Streamlit app running in Google Chrome (`streamlit run app.py`).
- [ ] Have Excel (or LibreOffice / Numbers) open to show the generated `.xlsx` output.
- [ ] Keep terminal visible for running `python evaluation.py`.
