import os
import urllib.request
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

# Custom Brand Colors
BRAND_COLOR = colors.HexColor('#1E3A8A')    # Deep Royal Blue (Corporate)
ACCENT_COLOR = colors.HexColor('#3B82F6')   # Bright Blue
TEXT_MAIN = colors.HexColor('#1E293B')      # Very Dark Slate
TEXT_MUTED = colors.HexColor('#64748B')     # Muted Gray
BG_LIGHT = colors.HexColor('#F8FAFC')       # Very Light Blue-Gray
BORDER_COLOR = colors.HexColor('#E2E8F0')   # Soft Gray

def download_logo(url: str, local_path: str):
    """Download logo image from external URL if local copy doesn't exist."""
    if not os.path.exists(local_path):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(local_path, 'wb') as out_file:
                out_file.write(response.read())
        except Exception as e:
            print(f"Warning: Could not download logo. Error: {e}")

def draw_background_and_header(canvas_obj, doc):
    """Draw corporate top header banner, footer accent line, logo, and company info."""
    canvas_obj.saveState()
    page_width, page_height = A4
    header_height = 1.4 * inch
    
    # 1. Top Header Banner
    canvas_obj.setFillColor(BRAND_COLOR)
    canvas_obj.rect(0, page_height - header_height, page_width, header_height, fill=1, stroke=0)
    
    # 2. Bottom Accent Line
    canvas_obj.setFillColor(BRAND_COLOR)
    canvas_obj.rect(0, 0, page_width, 0.2 * inch, fill=1, stroke=0)
    
    # 3. Logo in Header
    logo_path = "logo.png"
    if os.path.exists(logo_path):
        logo_height = 0.9 * inch
        logo_width = 2.7 * inch
        canvas_obj.drawImage(
            logo_path, 40, page_height - header_height + (header_height - logo_height)/2,
            width=logo_width, height=logo_height, preserveAspectRatio=True, mask='auto', anchor='w'
        )
    
    # 4. Company Header Details
    canvas_obj.setFillColor(colors.white)
    canvas_obj.setFont('Helvetica-Bold', 12)
    canvas_obj.drawRightString(page_width - 40, page_height - header_height/2 + 15, "Duniyape Technologies Private Limited")
    canvas_obj.setFont('Helvetica', 10)
    canvas_obj.drawRightString(page_width - 40, page_height - header_height/2 - 2, "Shop No-28, ModelTown, Phase-3,")
    canvas_obj.drawRightString(page_width - 40, page_height - header_height/2 - 17, "Bathinda-151001, Panjab, India")
    canvas_obj.setFont('Helvetica-Bold', 10)
    canvas_obj.drawRightString(page_width - 40, page_height - header_height/2 - 32, "GSTIN: 03AAKCD7304F1Z0")

    canvas_obj.restoreState()

def generate_pdf_invoice(filename: str, data: dict) -> str:
    """Generate a PDF invoice and return the absolute path to the generated document."""
    logo_url = "https://care2connect.in/assets/pp-BXFzvpwK.png"
    logo_path = "logo.png"
    download_logo(logo_url, logo_path)
    
    doc = SimpleDocTemplate(
        filename, 
        pagesize=A4, 
        rightMargin=40, 
        leftMargin=40, 
        topMargin=1.7 * inch, 
        bottomMargin=0.8 * inch
    )
    elements = []
    styles = getSampleStyleSheet()
    
    normal_style = ParagraphStyle(name='Normal', fontName='Helvetica', fontSize=10, textColor=TEXT_MAIN, leading=14)
    bold_style = ParagraphStyle(name='Bold', fontName='Helvetica-Bold', fontSize=10, textColor=TEXT_MAIN, leading=14)
    right_align = ParagraphStyle(name='Right', parent=normal_style, alignment=2)
    label_style = ParagraphStyle(name='Label', fontName='Helvetica-Bold', fontSize=9, textColor=TEXT_MUTED, leading=12)
    label_right = ParagraphStyle(name='LabelR', parent=label_style, alignment=2)
    tax_invoice_style = ParagraphStyle(name='TaxInvoice', fontName='Helvetica-Bold', fontSize=12, textColor=BRAND_COLOR, alignment=2)
    terms_style = ParagraphStyle(name='Terms', fontName='Helvetica', fontSize=8, textColor=TEXT_MUTED, leading=13)

    available_width = doc.width

    # --- 1. BILLING & INVOICE DETAILS ---
    bill_to_content = [
        Paragraph("BILLED TO", label_style),
        Spacer(1, 6),
        Paragraph(data['receiver_name'], bold_style),
        Paragraph(data['receiver_address'], normal_style),
        Paragraph(f"<b>Mobile:</b> {data['receiver_mobile']}", normal_style)
    ]
    
    invoice_details_content = [
        Paragraph("TAX INVOICE", tax_invoice_style),
        Spacer(1, 10),
        Paragraph("INVOICE DETAILS", label_right),
        Spacer(1, 6),
        Paragraph(f"<b>Invoice No:</b> {data['invoice_no']}", right_align),
        Paragraph(f"<b>Date:</b> {data['invoice_date']}", right_align),
    ]
    
    top_table = Table([[bill_to_content, invoice_details_content]], colWidths=[available_width/2, available_width/2])
    top_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    elements.append(top_table)
    elements.append(Spacer(1, 0.5 * inch))

    # --- 2. ITEMS TABLE ---
    table_data = [['#', 'ITEM DESCRIPTION', 'HSN / SAC', 'QTY', 'RATE', 'AMOUNT']]
    total_amount = 0.0
    for i, item in enumerate(data['items'], start=1):
        desc_text = f"<b>{item['product']}</b>"
        if item.get('description'):
            desc_text += f"<br/><font color='#64748B'>{item['description']}</font>"
        desc = Paragraph(desc_text, normal_style)
        hsn_sac = item.get('hsn_sac', '998599')
        
        table_data.append([
            str(i),
            desc,
            str(hsn_sac),
            str(item['qty']),
            f"Rs. {item['rate']:.2f}",
            f"Rs. {item['amount']:.2f}"
        ])
        total_amount += item['amount']
        
    col_widths = [0.35 * inch, 2.45 * inch, 0.85 * inch, 0.55 * inch, 1.35 * inch, 1.6 * inch]
    product_table = Table(table_data, colWidths=col_widths)
    product_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), BRAND_COLOR),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('ALIGN', (0,0), (2,0), 'LEFT'),
        ('ALIGN', (3,0), (-1,0), 'RIGHT'), 
        ('TOPPADDING', (0,0), (-1,0), 10),
        ('BOTTOMPADDING', (0,0), (-1,0), 10),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('TEXTCOLOR', (0,1), (-1,-1), TEXT_MAIN),
        ('TOPPADDING', (0,1), (-1,-1), 12),
        ('BOTTOMPADDING', (0,1), (-1,-1), 12),
        ('VALIGN', (0,1), (-1,-1), 'TOP'),
        ('ALIGN', (0,1), (2,-1), 'LEFT'),  
        ('ALIGN', (3,1), (5,-1), 'RIGHT'), 
        ('LINEBELOW', (0,0), (-1,-1), 1, BORDER_COLOR),
    ]))
    elements.append(product_table)
    elements.append(Spacer(1, 0.3 * inch))

    # --- 3. TOTALS & GST SECTION ---
    taxable_value = total_amount / 1.18
    cgst = taxable_value * 0.09
    sgst = taxable_value * 0.09
    total_gst = cgst + sgst
    
    totals_data = [
        [Paragraph("Taxable Value:", right_align), f"Rs. {taxable_value:.3f}"],
        [Paragraph("CGST (9%):", right_align), f"Rs. {cgst:.3f}"],
        [Paragraph("SGST (9%):", right_align), f"Rs. {sgst:.3f}"],
        [Paragraph("Total GST (18%):", right_align), f"Rs. {total_gst:.3f}"],
        [Paragraph("<b>GRAND TOTAL:</b>", right_align), f"Rs. {total_amount:.2f}"]
    ]
    totals_table = Table(totals_data, colWidths=[5.35 * inch, 1.8 * inch], hAlign='RIGHT')
    totals_table.setStyle(TableStyle([
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('FONTNAME', (1,0), (1,-2), 'Helvetica'),
        ('TEXTCOLOR', (0,0), (-1,-1), TEXT_MAIN),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('FONTNAME', (1,-1), (1,-1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0,-1), (-1,-1), BRAND_COLOR),
        ('BACKGROUND', (0,-1), (-1,-1), BG_LIGHT), 
        ('LINEABOVE', (0,-1), (-1,-1), 1.5, BRAND_COLOR),
        ('LINEBELOW', (0,-1), (-1,-1), 1.5, BRAND_COLOR),
        ('TOPPADDING', (0,-1), (-1,-1), 10),
        ('BOTTOMPADDING', (0,-1), (-1,-1), 10),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 0.6 * inch))

    # --- 4. FOOTER ---
    terms_text = """<b>Terms & Conditions</b><br/>
1. Please reference the Invoice ID in your payment details.<br/>
2. Subject To Bathinda Jurisdiction only.<br/>
3. No tax is payable under reverse charge for this invoice."""

    signatory_content = []
    seal_file = "seal.jpeg"
    if os.path.exists(seal_file):
        signatory_content.append(Image(seal_file, width=2.0 * inch, height=2.0 * inch, hAlign='RIGHT'))
        signatory_content.append(Spacer(1, 6))
    signatory_content.append(Paragraph("Authorized Signatory<br/><b>Duniyape Technologies Private Limited</b>", right_align))

    footer_table = Table([[Paragraph(terms_text, terms_style), signatory_content]], colWidths=[available_width * 0.55, available_width * 0.45])
    footer_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    elements.append(footer_table)
    
    doc.build(elements, onFirstPage=draw_background_and_header, onLaterPages=draw_background_and_header)
    return os.path.abspath(filename)
