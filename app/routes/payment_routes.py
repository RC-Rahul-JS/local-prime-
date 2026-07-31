from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from app.db import (
    get_loan_collection,
    get_disbursement_collection,
    get_emi_due_collection,
    get_payment_collection,
    get_penalty_collection
)

payment_bp = Blueprint('payment', __name__)

@payment_bp.route("/loan-disbursement", methods=["POST"])
def loan_disbursement():
    try:
        data = request.get_json() or {}
        loan_number = data.get("loan_number")
        disbursement_date_str = data.get("disbursement_date")
        payment_mode = data.get("payment_mode")
        transaction_id = data.get("transaction_id")

        if not loan_number:
            return jsonify({"success": False, "message": "loan_number is required"}), 400
        if not disbursement_date_str:
            return jsonify({"success": False, "message": "disbursement_date is required"}), 400

        try:
            disbursement_date = datetime.strptime(disbursement_date_str, "%Y-%m-%d")
        except Exception:
            return jsonify({"success": False, "message": "disbursement_date format should be YYYY-MM-DD"}), 400

        loan_coll = get_loan_collection()
        loan = loan_coll.find_one({"loan_number": loan_number})

        if not loan:
            return jsonify({"success": False, "message": "Loan not found"}), 404
        if loan.get("loan_status") != "SANCTIONED":
            return jsonify({"success": False, "message": "Loan is not sanctioned"}), 400
        if loan.get("disbursement_status") == "DISBURSED":
            return jsonify({"success": False, "message": "Loan already disbursed"}), 400

        loan_amount = float(loan.get("loan_amount", 0))
        processing_fee = float(loan.get("processing_fee", 0))
        net_disbursement = loan_amount - processing_fee

        loan_coll.update_one(
            {"_id": loan["_id"]},
            {"$set": {
                "loan_status": "DISBURSED",
                "disbursement_status": "DISBURSED",
                "disbursement_date": disbursement_date,
                "gross_disbursement": round(loan_amount),
                "processing_fee": round(processing_fee),
                "net_disbursement": round(net_disbursement),
                "payment_mode": payment_mode,
                "transaction_id": transaction_id,
                "bank_name": data.get("bank_name"),
                "account_number": data.get("account_number"),
                "ifsc_code": data.get("ifsc_code"),
                "remarks": data.get("remarks"),
                "updated_at": datetime.utcnow()
            }}
        )

        disbursement_coll = get_disbursement_collection()
        disbursement_coll.insert_one({
            "loan_id": loan["_id"],
            "loan_number": loan_number,
            "customer_id": loan.get("customer_id"),
            "loan_amount": round(loan_amount),
            "processing_fee": round(processing_fee),
            "net_disbursement": round(net_disbursement),
            "payment_mode": payment_mode,
            "transaction_id": transaction_id,
            "bank_name": data.get("bank_name"),
            "account_number": data.get("account_number"),
            "ifsc_code": data.get("ifsc_code"),
            "remarks": data.get("remarks"),
            "disbursement_date": disbursement_date,
            "created_at": datetime.utcnow()
        })

        if loan["frequency"] == "daily":
            next_interest_date = disbursement_date + timedelta(days=1)
        elif loan["frequency"] == "weekly":
            next_interest_date = disbursement_date + timedelta(days=7)
        elif loan["frequency"] == "monthly":
            next_interest_date = disbursement_date + relativedelta(months=1)
        else:
            next_interest_date = disbursement_date + relativedelta(months=1)

        loan_coll.update_one(
            {"_id": loan["_id"]},
            {"$set": {"next_interest_date": next_interest_date.strftime("%Y-%m-%d")}}
        )

        return jsonify({
            "success": True,
            "message": "Loan disbursed successfully",
            "loan_number": loan_number,
            "loan_amount": round(loan_amount),
            "processing_fee": round(processing_fee),
            "net_disbursement": round(net_disbursement),
            "loan_status": "DISBURSED",
            "disbursement_status": "DISBURSED"
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@payment_bp.route("/generate-emi-due", methods=["POST"])
def generate_emi_due():
    try:
        data = request.get_json() or {}
        loan_number = data.get("loan_number")
        due_date = data.get("due_date")

        if not loan_number or not due_date:
            return jsonify({"success": False, "message": "loan_number and due_date are required"}), 400

        try:
            due_date_obj = datetime.strptime(due_date, "%Y-%m-%d")
        except Exception:
            return jsonify({"success": False, "message": "Invalid due_date format (YYYY-MM-DD)"}), 400

        loan_coll = get_loan_collection()
        emi_coll = get_emi_due_collection()
        penalty_coll = get_penalty_collection()

        loan = loan_coll.find_one({"loan_number": loan_number})
        if not loan:
            return jsonify({"success": False, "message": "Loan not found"}), 404
        if loan["loan_status"] != "DISBURSED":
            return jsonify({"success": False, "message": "Loan is not disbursed"}), 400
        if loan["loan_status"] == "CLOSED":
            return jsonify({"success": False, "message": "Loan already closed"}), 400

        outstanding_principal = float(loan.get("outstanding_principal", 0))
        if outstanding_principal <= 0:
            return jsonify({"success": False, "message": "Loan already paid"}), 400

        already = emi_coll.find_one({"loan_number": loan_number, "due_date": due_date})
        if already:
            return jsonify({"success": False, "message": "EMI already generated"}), 400

        previous_emi = emi_coll.find_one({"loan_number": loan_number}, sort=[("emi_number", -1)])
        penalty_added = 0

        if previous_emi and previous_emi.get("status") != "PAID":
            old_due = datetime.strptime(previous_emi["due_date"], "%Y-%m-%d")
            delay_days = (due_date_obj - old_due).days
            if delay_days > 5:
                penalty_days = delay_days - 5
                penalty_added = penalty_days * 100

                already_penalty = penalty_coll.find_one({
                    "loan_number": loan_number,
                    "emi_number": previous_emi["emi_number"]
                })
                if not already_penalty:
                    penalty_coll.insert_one({
                        "loan_id": loan["_id"],
                        "loan_number": loan_number,
                        "customer_id": loan["customer_id"],
                        "emi_number": previous_emi["emi_number"],
                        "due_date": previous_emi["due_date"],
                        "posting_date": due_date,
                        "delay_days": penalty_days,
                        "penalty_type": "daily",
                        "penalty_value": 100,
                        "penalty_amount": penalty_added,
                        "status": "UNPAID",
                        "created_at": datetime.utcnow()
                    })
                    loan_coll.update_one(
                        {"_id": loan["_id"]},
                        {"$inc": {"penalty_outstanding": penalty_added}}
                    )

        # Refresh loan state
        loan = loan_coll.find_one({"_id": loan["_id"]})
        installment = float(loan.get("installment", 0))
        interest_due = round(float(loan.get("interest_outstanding", 0)), 2)

        principal_due = installment - interest_due
        if principal_due < 0:
            principal_due = 0
        if principal_due > outstanding_principal:
            principal_due = outstanding_principal
        principal_due = round(principal_due, 2)

        remaining_balance = round(outstanding_principal - principal_due, 2)
        emi_number = emi_coll.count_documents({"loan_number": loan_number}) + 1
        total_penalty = round(float(loan.get("penalty_outstanding", 0)), 2)
        total_due = round(principal_due + interest_due + total_penalty, 2)

        emi_coll.insert_one({
            "loan_id": loan["_id"],
            "loan_number": loan_number,
            "customer_id": loan["customer_id"],
            "emi_number": emi_number,
            "due_date": due_date,
            "installment": round(installment, 2),
            "principal_due": principal_due,
            "interest_due": interest_due,
            "penalty_due": total_penalty,
            "total_due": total_due,
            "remaining_balance": remaining_balance,
            "interest_rate": loan["interest_rate"],
            "frequency": loan["frequency"],
            "status": "UNPAID",
            "created_at": datetime.utcnow()
        })

        return jsonify({
            "success": True,
            "message": "EMI generated successfully",
            "loan_number": loan_number,
            "emi_number": emi_number,
            "due_date": due_date,
            "installment": round(installment, 2),
            "principal_due": principal_due,
            "interest_due": interest_due,
            "penalty_due": total_penalty,
            "penalty_added_this_cycle": penalty_added,
            "total_due": total_due,
            "remaining_balance": remaining_balance,
            "status": "UNPAID"
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@payment_bp.route("/customer-payment", methods=["POST"])
def customer_payment():
    try:
        data = request.get_json() or {}
        loan_number = data.get("loan_number")
        emi_number = data.get("emi_number")
        payment_amount = float(data.get("payment_amount", 0))

        if not loan_number or emi_number is None:
            return jsonify({"success": False, "message": "loan_number and emi_number are required"}), 400
        if payment_amount <= 0:
            return jsonify({"success": False, "message": "Invalid payment amount"}), 400

        loan_coll = get_loan_collection()
        emi_coll = get_emi_due_collection()
        payment_coll = get_payment_collection()

        loan = loan_coll.find_one({"loan_number": loan_number})
        if not loan:
            return jsonify({"success": False, "message": "Loan not found"}), 404
        if loan.get("loan_status") == "CLOSED":
            return jsonify({"success": False, "message": "Loan already closed"}), 400

        emi = emi_coll.find_one({"loan_number": loan_number, "emi_number": emi_number})
        if not emi:
            return jsonify({"success": False, "message": "EMI not found"}), 404
        if emi.get("status") == "PAID":
            return jsonify({"success": False, "message": "EMI already paid"}), 400

        interest_due = float(emi.get("interest_due", 0))
        principal_due = float(emi.get("principal_due", 0))
        penalty_due = float(loan.get("penalty_outstanding", 0))

        balance = payment_amount

        # Waterfall Payment Allocation: Penalty -> Interest -> Principal
        penalty_paid = min(balance, penalty_due)
        balance -= penalty_paid

        interest_paid = min(balance, interest_due)
        balance -= interest_paid

        principal_paid = min(balance, principal_due)
        balance -= principal_paid

        new_principal = round(float(loan.get("outstanding_principal", 0)) - principal_paid, 2)
        new_interest = round(float(loan.get("interest_outstanding", 0)) - interest_paid, 2)
        new_penalty = round(penalty_due - penalty_paid, 2)

        loan_coll.update_one(
            {"_id": loan["_id"]},
            {"$set": {
                "outstanding_principal": max(new_principal, 0),
                "interest_outstanding": max(new_interest, 0),
                "penalty_outstanding": max(new_penalty, 0),
                "updated_at": datetime.utcnow()
            }}
        )

        total_due = principal_due + interest_due
        paid_amount = principal_paid + interest_paid
        emi_status = "PAID" if paid_amount >= total_due else "PARTIAL"

        emi_coll.update_one(
            {"_id": emi["_id"]},
            {"$set": {
                "status": emi_status,
                "paid_date": data.get("payment_date", datetime.now().strftime("%Y-%m-%d")),
                "principal_paid": principal_paid,
                "interest_paid": interest_paid,
                "penalty_paid": penalty_paid,
                "payment_amount": payment_amount
            }}
        )

        payment_coll.insert_one({
            "loan_id": loan["_id"],
            "loan_number": loan_number,
            "emi_number": emi_number,
            "customer_id": loan["customer_id"],
            "payment_date": data.get("payment_date", datetime.now().strftime("%Y-%m-%d")),
            "payment_amount": payment_amount,
            "principal_paid": principal_paid,
            "interest_paid": interest_paid,
            "penalty_paid": penalty_paid,
            "payment_mode": data.get("payment_mode"),
            "transaction_id": data.get("transaction_id"),
            "created_at": datetime.utcnow()
        })

        is_closed = (max(new_principal, 0) == 0 and max(new_interest, 0) == 0 and max(new_penalty, 0) == 0)
        if is_closed:
            loan_coll.update_one(
                {"_id": loan["_id"]},
                {"$set": {
                    "loan_status": "CLOSED",
                    "closure_date": datetime.now().strftime("%Y-%m-%d"),
                    "updated_at": datetime.utcnow()
                }}
            )

        return jsonify({
            "success": True,
            "loan_number": loan_number,
            "emi_number": emi_number,
            "payment_amount": payment_amount,
            "principal_paid": principal_paid,
            "interest_paid": interest_paid,
            "penalty_paid": penalty_paid,
            "remaining_principal": max(new_principal, 0),
            "remaining_interest": max(new_interest, 0),
            "remaining_penalty": max(new_penalty, 0),
            "emi_status": emi_status,
            "loan_status": "CLOSED" if is_closed else "DISBURSED"
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@payment_bp.route("/penalty-posting", methods=["POST"])
def penalty_posting():
    try:
        data = request.get_json() or {}
        loan_number = data.get("loan_number")
        posting_date_str = data.get("posting_date")
        penalty_type = data.get("penalty_type", "daily")
        penalty_value = float(data.get("penalty_value", 100))

        if not loan_number or not posting_date_str:
            return jsonify({"success": False, "message": "loan_number and posting_date are required"}), 400

        posting_date = datetime.strptime(posting_date_str, "%Y-%m-%d")
        loan_coll = get_loan_collection()
        emi_coll = get_emi_due_collection()
        penalty_coll = get_penalty_collection()

        loan = loan_coll.find_one({"loan_number": loan_number})
        if not loan:
            return jsonify({"success": False, "message": "Loan not found"}), 404

        emi = emi_coll.find_one({"loan_number": loan_number, "status": "UNPAID"})
        if not emi:
            return jsonify({"success": False, "message": "No unpaid EMI found"}), 404

        due_date = datetime.strptime(emi["due_date"], "%Y-%m-%d")
        delay_days = (posting_date - due_date).days
        if delay_days <= 0:
            return jsonify({"success": False, "message": "Penalty not applicable"}), 400

        already = penalty_coll.find_one({"loan_number": loan_number, "due_date": emi["due_date"]})
        if already:
            return jsonify({"success": False, "message": "Penalty already posted"}), 400

        installment = float(emi["installment"])
        penalty_amount = delay_days * penalty_value if penalty_type == "daily" else (installment * penalty_value / 100)
        penalty_amount = round(penalty_amount, 2)

        penalty_coll.insert_one({
            "loan_id": loan["_id"],
            "loan_number": loan_number,
            "customer_id": loan["customer_id"],
            "due_date": emi["due_date"],
            "posting_date": posting_date,
            "delay_days": delay_days,
            "penalty_type": penalty_type,
            "penalty_value": penalty_value,
            "penalty_amount": penalty_amount,
            "status": "UNPAID",
            "created_at": datetime.utcnow()
        })

        loan_coll.update_one(
            {"_id": loan["_id"]},
            {
                "$inc": {"penalty_outstanding": penalty_amount},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )

        return jsonify({
            "success": True,
            "loan_number": loan_number,
            "due_date": emi["due_date"],
            "delay_days": delay_days,
            "penalty_amount": penalty_amount,
            "penalty_outstanding": loan.get("penalty_outstanding", 0) + penalty_amount
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
