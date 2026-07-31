"""
Invoice Generator CLI Entrypoint Proxy (Backwards Compatibility)
Restructured under Modular Architecture (app package)
"""
import os
from app.services.invoice_service import generate_pdf_invoice

if __name__ == '__main__':
    invoice_data = {
        'invoice_no': 'INV-2023-0001',
        'invoice_date': '24 Oct 2023',
        'receiver_name': 'John Doe',
        'receiver_mobile': '+91 98765 43210',
        'receiver_address': '123, Model Town, Phase 1, City, State, India',
        'items': [
            {
                'product': 'Platform Fees',
                'description': '',
                'hsn_sac': '998599',
                'qty': 1,
                'rate': 20.00,
                'amount': 20.00
            }
        ]
    }
    
    output_pdf = 'Duniyape_Invoice.pdf'
    pdf_path = generate_pdf_invoice(output_pdf, invoice_data)
    print(f"Ultra-premium GST invoice generated successfully at: {pdf_path}")
