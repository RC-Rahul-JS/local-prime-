from flask import Blueprint, request, jsonify
from datetime import datetime
import uuid
from app.db import get_loan_collection, get_emi_due_collection
from app.services.loan_service import calculate_loan_schedule, get_periods_per_year

loan_bp = Blueprint('loan', __name__)

@loan_bp.route("/loan-calculator", methods=["POST"])
def loan_calculator():
    try:
        data = request.get_json() or {}
        principal = float(data.get("loan_amount", 0))
        annual_rate = float(data.get("interest_rate", 0))
        tenure = int(data.get("tenure", 0))
        frequency = data.get("frequency", "monthly").lower()
        interest_type = data.get("interest_type", "reducing").lower()

        if principal <= 0:
            return jsonify({"success": False, "message": "Invalid loan amount"}), 400
        if annual_rate < 0:
            return jsonify({"success": False, "message": "Invalid interest rate"}), 400
        if tenure <= 0:
            return jsonify({"success": False, "message": "Invalid tenure"}), 400

        result = calculate_loan_schedule(principal, annual_rate, tenure, frequency, interest_type)
        result["success"] = True
        return jsonify(result), 200

    except ValueError as ve:
        return jsonify({"success": False, "message": str(ve)}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@loan_bp.route("/loan-sanction", methods=["POST"])
def loan_sanction():
    try:
        data = request.get_json() or {}
        customer_id = data.get("customer_id")
        principal = float(data.get("loan_amount", 0))
        annual_rate = float(data.get("interest_rate", 0))
        tenure = int(data.get("tenure", 0))
        frequency = data.get("frequency", "monthly").lower()
        interest_type = data.get("interest_type", "reducing").lower()
        processing_fee = float(data.get("processing_fee", 0))
        purpose = data.get("purpose", "")
        sanction_date = data.get("sanction_date", datetime.now().strftime("%Y-%m-%d"))
        first_installment_date = data.get("first_installment_date")

        if not customer_id:
            return jsonify({"success": False, "message": "customer_id is required"}), 400
        if principal <= 0:
            return jsonify({"success": False, "message": "Invalid loan amount"}), 400
        if tenure <= 0:
            return jsonify({"success": False, "message": "Invalid tenure"}), 400

        periods_per_year = get_periods_per_year(frequency)
        period_rate = annual_rate / (periods_per_year * 100)

        if interest_type == "flat":
            total_interest = principal * period_rate * tenure
            total_payment = principal + total_interest
            installment = total_payment / tenure
        elif interest_type == "reducing":
            if period_rate == 0:
                installment = principal / tenure
            else:
                installment = (
                    principal * period_rate * pow((1 + period_rate), tenure)
                ) / (pow((1 + period_rate), tenure) - 1)
            total_payment = installment * tenure
            total_interest = total_payment - principal
        else:
            return jsonify({"success": False, "message": "Invalid interest type"}), 400

        loan_number = "LN" + datetime.now().strftime("%Y%m%d") + uuid.uuid4().hex[:6].upper()

        document = {
            "loan_number": loan_number,
            "customer_id": customer_id,
            "purpose": purpose,
            "loan_amount": round(principal),
            "outstanding_principal": round(principal),
            "interest_rate": annual_rate,
            "interest_type": interest_type,
            "frequency": frequency,
            "tenure": tenure,
            "processing_fee": round(processing_fee),
            "installment": round(installment),
            "total_interest": round(total_interest),
            "total_payment": round(total_payment),
            "sanction_date": sanction_date,
            "first_installment_date": first_installment_date,
            "next_interest_date": first_installment_date,
            "loan_status": "SANCTIONED",
            "disbursement_status": "PENDING",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }

        loan_coll = get_loan_collection()
        result = loan_coll.insert_one(document)

        return jsonify({
            "success": True,
            "loan_id": str(result.inserted_id),
            "loan_number": loan_number,
            "loan_status": "SANCTIONED",
            "installment": round(installment),
            "total_interest": round(total_interest),
            "total_payment": round(total_payment)
        }), 200

    except ValueError as ve:
        return jsonify({"success": False, "message": str(ve)}), 400
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@loan_bp.route("/loan-closure-list", methods=["GET"])
def loan_closure_list():
    try:
        loan_coll = get_loan_collection()
        emi_coll = get_emi_due_collection()
        loans = loan_coll.find({
            "loan_status": "DISBURSED",
            "outstanding_principal": 0,
            "interest_outstanding": {"$in": [0, 0.0, None]},
            "penalty_outstanding": {"$in": [0, 0.0, None]}
        })

        data = []
        for loan in loans:
            unpaid_emi = emi_coll.count_documents({
                "loan_number": loan["loan_number"],
                "status": "UNPAID"
            })
            if unpaid_emi > 0:
                continue

            total_paid = loan.get("loan_amount", 0) + loan.get("total_interest", 0) + loan.get("penalty_paid", 0)
            data.append({
                "loan_number": loan["loan_number"],
                "customer_id": loan["customer_id"],
                "loan_amount": loan["loan_amount"],
                "interest_rate": loan["interest_rate"],
                "frequency": loan["frequency"],
                "sanction_date": loan.get("sanction_date"),
                "disbursement_date": loan.get("disbursement_date"),
                "outstanding_principal": loan.get("outstanding_principal", 0),
                "interest_outstanding": loan.get("interest_outstanding", 0),
                "penalty_outstanding": loan.get("penalty_outstanding", 0),
                "total_paid": total_paid,
                "eligible_for_closure": True
            })

        return jsonify({
            "success": True,
            "total_records": len(data),
            "data": data
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@loan_bp.route("/loan-closure", methods=["POST"])
def loan_closure():
    try:
        data = request.get_json() or {}
        loan_number = data.get("loan_number")
        closure_date = data.get("closure_date", datetime.now().strftime("%Y-%m-%d"))
        closed_by = data.get("closed_by", "SYSTEM")
        remarks = data.get("remarks", "")

        if not loan_number:
            return jsonify({"success": False, "message": "loan_number is required"}), 400

        loan_coll = get_loan_collection()
        emi_coll = get_emi_due_collection()

        loan = loan_coll.find_one({"loan_number": loan_number})
        if not loan:
            return jsonify({"success": False, "message": "Loan not found"}), 404
        if loan["loan_status"] == "CLOSED":
            return jsonify({"success": False, "message": "Loan already closed"}), 400
        if loan["loan_status"] != "DISBURSED":
            return jsonify({"success": False, "message": "Only disbursed loans can be closed"}), 400

        if float(loan.get("outstanding_principal", 0)) > 0:
            return jsonify({"success": False, "message": "Outstanding principal exists"}), 400
        if float(loan.get("interest_outstanding", 0)) > 0:
            return jsonify({"success": False, "message": "Outstanding interest exists"}), 400
        if float(loan.get("penalty_outstanding", 0)) > 0:
            return jsonify({"success": False, "message": "Outstanding penalty exists"}), 400

        unpaid_emi = emi_coll.count_documents({"loan_number": loan_number, "status": "UNPAID"})
        if unpaid_emi > 0:
            return jsonify({"success": False, "message": "Unpaid EMI exists"}), 400

        loan_coll.update_one(
            {"_id": loan["_id"]},
            {"$set": {
                "loan_status": "CLOSED",
                "closure_date": closure_date,
                "closed_by": closed_by,
                "closure_remarks": remarks,
                "next_interest_date": None,
                "updated_at": datetime.utcnow()
            }}
        )

        return jsonify({
            "success": True,
            "message": "Loan closed successfully",
            "loan_number": loan_number,
            "loan_status": "CLOSED",
            "closure_date": closure_date,
            "closed_by": closed_by
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
