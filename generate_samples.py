"""
Generates 3 rich sample PDF test documents for the INCUXAI AI Agent Challenge:
1. sample_1_financial_statement.pdf: Multi-page continuous ledger (4 pages, running balance, repeating headers)
2. sample_2_inventory_order_report.pdf: Wide table with 12 columns (>10 cols requirement) across 3 pages
3. sample_3_scanned_invoice.pdf: Scanned logistics invoice rendered as raster image with authentic scanner attributes
"""

import os
import random
from reportlab.lib.pagesizes import letter, landscape, A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import pymupdf
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


SAMPLES_DIR = os.path.dirname(os.path.abspath(__file__))


def create_sample_1_financial_statement():
    """Multi-page bank statement across 4 pages with running balances and repeating headers."""
    pdf_path = os.path.join(SAMPLES_DIR, "sample_1_financial_statement.pdf")
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=40,
        bottomMargin=40
    )
    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#1B365D')
    )
    subtitle_style = ParagraphStyle(
        'DocSub',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#555555')
    )

    elements.append(Paragraph("<b>INCUXAI GLOBAL BANKING CORP</b> - Corporate Account Statement", title_style))
    elements.append(Paragraph("Account No: 9876-5432-1098 | Currency: INR | Period: 01-Jan-2026 to 28-Feb-2026", subtitle_style))
    elements.append(Spacer(1, 15))

    headers = ['Txn Date', 'Value Date', 'Reference No', 'Description', 'Withdrawals (INR)', 'Deposits (INR)', 'Balance (INR)']
    
    tx_descriptions = [
        "Vendor Pmt - Cloud Hosting AWS", "Client Wire - Global Logistics Ltd", "Office Lease - Feb 2026",
        "Payroll Direct Deposit - Engineering", "Software Subscription - GitHub Enterprise", "Consulting Fee - Acme Corp",
        "Utility Payment - Electric Grid", "Travel Reimbursement - Sales Team", "Equipment Purchase - Workstations",
        "Dividend Payout - Series B", "Tax Remittance - GST Q4", "Marketing Campaign - Search Ads"
    ]

    data = [headers]
    curr_balance = 250000.0
    random.seed(42)

    total_withdrawals = 0.0
    total_deposits = 0.0

    for i in range(1, 56):
        date_str = f"2026-{1 + (i//30):02d}-{(i % 28) + 1:02d}"
        val_date = date_str
        ref_no = f"TXN-{100000 + i}"
        desc = tx_descriptions[i % len(tx_descriptions)]

        is_deposit = (i % 3 == 0)
        if is_deposit:
            dep_amt = round(random.uniform(15000, 85000), 2)
            with_amt = 0.0
            curr_balance += dep_amt
            total_deposits += dep_amt
            dep_str = f"{dep_amt:,.2f}"
            with_str = "-"
        else:
            with_amt = round(random.uniform(2000, 42000), 2)
            dep_amt = 0.0
            curr_balance -= with_amt
            total_withdrawals += with_amt
            with_str = f"{with_amt:,.2f}"
            dep_str = "-"

        bal_str = f"{curr_balance:,.2f}"
        data.append([date_str, val_date, ref_no, desc, with_str, dep_str, bal_str])

    # Summary Total Row
    data.append(["TOTAL", "", "", "Statement Period Totals", f"{total_withdrawals:,.2f}", f"{total_deposits:,.2f}", f"{curr_balance:,.2f}"])

    rows_per_page = 16
    for page_num in range(4):
        start = page_num * rows_per_page
        end = min((page_num + 1) * rows_per_page, len(data))
        if start >= len(data):
            break

        page_data = [headers] if page_num > 0 else []
        page_data.extend(data[start:end])

        t = Table(page_data, colWidths=[65, 65, 75, 140, 80, 80, 85], repeatRows=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1B365D')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (2, -1), 'CENTER'),
            ('ALIGN', (3, 0), (3, -1), 'LEFT'),
            ('ALIGN', (4, 0), (-1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 1), (-1, -1), 7.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 3),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D3D9DE')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F7F9FC')])
        ]))

        elements.append(t)
        if page_num < 3:
            elements.append(PageBreak())
            elements.append(Paragraph(f"<b>INCUXAI GLOBAL BANKING CORP</b> - Continued Statement (Page {page_num + 2} of 4)", subtitle_style))
            elements.append(Spacer(1, 10))

    doc.build(elements)
    print(f"Generated Sample 1: {pdf_path}")
    return pdf_path


def create_sample_2_inventory_order_report():
    """Wide table with 12 columns (>10 cols) across 3 landscape pages."""
    pdf_path = os.path.join(SAMPLES_DIR, "sample_2_inventory_order_report.pdf")
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=landscape(A4),
        leftMargin=25,
        rightMargin=25,
        topMargin=30,
        bottomMargin=30
    )
    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle(
        'DocTitle2',
        parent=styles['Heading1'],
        fontSize=15,
        leading=18,
        textColor=colors.HexColor('#1B365D')
    )
    elements.append(Paragraph("<b>GLOBAL LOGISTICS & SUPPLY CHAIN - MASTER INVENTORY REPORT</b>", title_style))
    elements.append(Paragraph("12-Column Comprehensive Stock, Valuation & Replenishment Audit | Facility: Hub Central 01", styles['Normal']))
    elements.append(Spacer(1, 12))

    # 12 columns
    headers = [
        'Item SKU', 'Product Name', 'Category', 'WH Loc', 'Bin #',
        'Units In Stock', 'Units On Order', 'Unit Cost ($)', 'Retail Price ($)',
        'Discount (%)', 'Tax Rate (%)', 'Total Value ($)'
    ]

    items = [
        ("SKU-101", "Precision Stepper Motor 24V", "Industrial", "WH-A", "B-12", 45, 10, 32.50, 55.00, 5, 18),
        ("SKU-102", "Optocoupler Array SMD-8", "Electronics", "WH-A", "B-14", 120, 50, 4.20, 8.50, 0, 18),
        ("SKU-103", "Anodized Aluminum Bracket 50mm", "Hardware", "WH-B", "C-01", 80, 20, 12.00, 22.00, 10, 12),
        ("SKU-104", "Lithium Polymer Pack 5000mAh", "Electronics", "WH-C", "D-09", 35, 15, 28.00, 49.00, 0, 18),
        ("SKU-105", "Thermal Paste Compound 30g", "Hardware", "WH-A", "B-03", 200, 100, 3.50, 7.00, 15, 18),
        ("SKU-106", "Microcontroller Board v4.2", "Electronics", "WH-A", "B-22", 60, 40, 18.50, 34.00, 5, 18),
        ("SKU-107", "Corrugated Heavy Duty Box XL", "Packaging", "WH-D", "E-05", 500, 250, 1.80, 3.20, 0, 5),
        ("SKU-108", "High-Torque Planetary Gearbox", "Industrial", "WH-B", "C-11", 25, 5, 75.00, 130.00, 8, 18),
        ("SKU-109", "Silicone Thermal Pad 100x100", "Hardware", "WH-A", "B-07", 150, 50, 2.10, 4.50, 0, 12),
        ("SKU-110", "Fiber Optic Patch Cable 5m", "Electronics", "WH-C", "D-18", 90, 30, 8.40, 15.00, 10, 18),
        ("SKU-111", "M4 Stainless Hex Bolts (100pk)", "Hardware", "WH-B", "C-04", 300, 100, 5.00, 9.90, 0, 12),
        ("SKU-112", "Solid State Relay 40A AC", "Industrial", "WH-A", "B-19", 40, 20, 22.00, 39.00, 5, 18),
    ]

    all_rows = []
    for page_idx in range(3):
        for idx, item in enumerate(items):
            sku = f"SKU-{200 + page_idx*20 + idx}"
            name = item[1]
            cat = item[2]
            wh = item[3]
            bin_no = f"{item[4]}-{page_idx+1}"
            stock = item[5] + (page_idx * 5)
            order = item[6]
            cost = item[7]
            retail = item[8]
            disc = item[9]
            tax = item[10]

            tot_val = round(stock * cost, 2)
            # Intentional math error at row 12 for validation testing
            if page_idx == 0 and idx == 11:
                tot_val = round(tot_val + 250.0, 2)

            all_rows.append([
                sku, name, cat, wh, bin_no,
                str(stock), str(order), f"${cost:.2f}", f"${retail:.2f}",
                f"{disc}%", f"{tax}%", f"${tot_val:.2f}"
            ])

    rows_per_page = 12
    for p_idx in range(3):
        start = p_idx * rows_per_page
        end = (p_idx + 1) * rows_per_page
        page_table_data = [headers] + all_rows[start:end]

        t = Table(
            page_table_data,
            colWidths=[55, 135, 70, 45, 45, 70, 70, 60, 65, 55, 55, 75]
        )
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1B365D')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (4, -1), 'LEFT'),
            ('ALIGN', (5, 0), (-1, -1), 'RIGHT'),
            ('FONTSIZE', (0, 1), (-1, -1), 7.5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D3D9DE')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F7F9FC')])
        ]))

        elements.append(t)
        if p_idx < 2:
            elements.append(PageBreak())
            elements.append(Paragraph(f"<b>MASTER INVENTORY REPORT</b> - Continued (Page {p_idx + 2} of 3)", styles['Normal']))
            elements.append(Spacer(1, 10))

    doc.build(elements)
    print(f"Generated Sample 2: {pdf_path}")
    return pdf_path


def create_sample_3_scanned_invoice():
    """Generates an authentic image-based scanned PDF with scanner attributes."""
    pdf_path = os.path.join(SAMPLES_DIR, "sample_3_scanned_invoice.pdf")
    
    temp_clean_pdf = os.path.join(SAMPLES_DIR, "_temp_clean_inv.pdf")
    doc = SimpleDocTemplate(
        temp_clean_pdf,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40
    )
    styles = getSampleStyleSheet()
    elements = []

    title_style = ParagraphStyle(
        'InvTitle',
        parent=styles['Heading1'],
        fontSize=18,
        leading=22,
        textColor=colors.black
    )
    elements.append(Paragraph("<b>TAX INVOICE & FREIGHT BILL</b>", title_style))
    elements.append(Paragraph("APEX INDUSTRIAL SUPPLIES LTD | GSTIN: 27AABCA1234F1Z5", styles['Normal']))
    elements.append(Paragraph("Invoice No: INV-2026-8841 | Date: 12-Oct-2026 | Due Date: 11-Nov-2026", styles['Normal']))
    elements.append(Spacer(1, 15))

    invoice_headers = ['Item #', 'Description of Goods', 'HSN/SAC', 'Quantity', 'Unit Rate ($)', 'Amount ($)']
    invoice_rows = [
        invoice_headers,
        ['1', 'Heavy Duty Hydraulic Valve 3/4"', '84812000', '15', '120.00', '1,800.00'],
        ['2', 'Pneumatic Actuator Double Acting', '84123100', '8', '245.50', '1,964.00'],
        ['3', 'High Pressure Steel Flange 150#', '73079100', '30', '45.00', '1,350.00'],
        ['4', 'Spiral Wound Gasket Ring 2"', '84841000', '50', '12.50', '625.00'],
        ['5', 'Industrial Lubricant ISO VG 68 20L', '27101990', '4', '85.00', '340.00'],
        ['6', 'Freight, Handling & Insurance', '996511', '1', '250.00', '250.00'],
        ['TOTAL', '', '', '', '', '6,329.00']
    ]

    t = Table(invoice_rows, colWidths=[50, 210, 75, 55, 70, 75])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#222222')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('ALIGN', (2, 0), (2, -1), 'CENTER'),
        ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#666666')),
        ('FONTSIZE', (0, 1), (-1, -1), 8.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("<b>Payment Terms:</b> Net 30 days. Wire transfer to Account # 4455-8899-0012.", styles['Normal']))
    elements.append(Paragraph("Authorized Signatory: Apex Logistics Finance Dept", styles['Normal']))

    doc.build(elements)

    # Rasterize to pure image at 300 DPI to create genuine image-based PDF
    fitz_doc = pymupdf.open(temp_clean_pdf)
    page = fitz_doc[0]
    pix = page.get_pixmap(dpi=300)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    # Authentic scanner attributes: subtle paper warmth and light edge shadow
    scanner_bg = Image.new("RGB", img.size, (253, 252, 250))
    scanner_bg.paste(img, (0, 0))

    draw = ImageDraw.Draw(scanner_bg)
    draw.line([(0, 0), (scanner_bg.width, 0)], fill=(215, 215, 215), width=2)

    # Save as scanned PDF (pure raster image, no selectable text)
    scanner_bg.save(pdf_path, "PDF", resolution=300.0)
    fitz_doc.close()
    if os.path.exists(temp_clean_pdf):
        os.remove(temp_clean_pdf)

    print(f"Generated Sample 3 (Scanned OCR): {pdf_path}")
    return pdf_path


if __name__ == "__main__":
    create_sample_1_financial_statement()
    create_sample_2_inventory_order_report()
    create_sample_3_scanned_invoice()
    print("All 3 test sample PDFs generated successfully!")
