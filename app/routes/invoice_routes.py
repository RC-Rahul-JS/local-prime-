from flask import Blueprint, request, jsonify, send_file
import os
from app.services.invoice_service import generate_pdf_invoice

invoice_bp = Blueprint('invoice', __name__)

@invoice_bp.route("/generate-invoice", methods=["POST"])
def generate_invoice():
    try:
        data = request.get_json() or {}
        
        # Default fallback sample data if not provided
        invoice_data = {
            'invoice_no': data.get('invoice_no', 'INV-2023-0001'),
            'invoice_date': data.get('invoice_date', '24 Oct 2023'),
            'receiver_name': data.get('receiver_name', 'John Doe'),
            'receiver_mobile': data.get('receiver_mobile', '+91 98765 43210'),
            'receiver_address': data.get('receiver_address', '123, Model Town, Phase 1, City, State, India'),
            'items': data.get('items', [
                {
                    'product': 'Platform Fees',
                    'description': '',
                    'hsn_sac': '998599',
                    'qty': 1,
                    'rate': 20.00,
                    'amount': 20.00
                }
            ])
        }

        output_filename = data.get('output_filename', 'Duniyape_Invoice.pdf')
        pdf_path = generate_pdf_invoice(output_filename, invoice_data)

        if data.get('download') is True:
            return send_file(pdf_path, as_attachment=True)

        return jsonify({
            "success": True,
            "message": "Invoice PDF generated successfully",
            "file_name": os.path.basename(pdf_path),
            "file_path": pdf_path
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
