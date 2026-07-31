from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from app.db import get_loan_collection, get_interest_collection

interest_bp = Blueprint('interest', __name__)

@interest_bp.route("/interest-posting", methods=["POST"])
def interest_posting():
    try:
        data = request.get_json() or {}
        loan_number = data.get("loan_number")

        if not loan_number:
            return jsonify({"success": False, "message": "loan_number required"}), 400

        loan_coll = get_loan_collection()
        interest_coll = get_interest_collection()

        loan = loan_coll.find_one({"loan_number": loan_number})
        if not loan:
            return jsonify({"success": False, "message": "Loan not found"}), 404
        if loan.get("loan_status") != "DISBURSED":
            return jsonify({"success": False, "message": "Loan not disbursed"}), 400

        exists = interest_coll.find_one({
            "loan_number": loan_number,
            "posting_date": {
                "$gte": datetime.combine(datetime.today(), datetime.min.time()),
                "$lt": datetime.combine(datetime.today(), datetime.max.time())
            }
        })
        if exists:
            return jsonify({"success": False, "message": "Interest already posted today."}), 400

        principal = float(loan.get("outstanding_principal", 0))
        annual_rate = float(loan.get("interest_rate", 0))
        frequency = loan.get("frequency", "monthly").lower()
        posting_date = datetime.strptime(loan["next_interest_date"], "%Y-%m-%d")

        if frequency == "daily":
            interest = principal * annual_rate / (365 * 100)
            next_date = posting_date + timedelta(days=1)
        elif frequency == "weekly":
            interest = principal * annual_rate / (52 * 100)
            next_date = posting_date + timedelta(days=7)
        elif frequency == "monthly":
            interest = principal * annual_rate / (12 * 100)
            next_date = posting_date + relativedelta(months=1)
        else:
            return jsonify({"success": False, "message": "Invalid frequency"}), 400

        interest = round(interest, 2)

        interest_coll.insert_one({
            "loan_id": loan["_id"],
            "loan_number": loan_number,
            "customer_id": loan["customer_id"],
            "posting_date": posting_date,
            "interest_amount": interest,
            "principal": principal,
            "interest_rate": annual_rate,
            "frequency": frequency,
            "status": "UNPAID",
            "created_at": datetime.utcnow()
        })

        loan_coll.update_one(
            {"_id": loan["_id"]},
            {
                "$inc": {"interest_outstanding": interest},
                "$set": {
                    "next_interest_date": next_date.strftime("%Y-%m-%d"),
                    "updated_at": datetime.utcnow()
                }
            }
        )

        return jsonify({
            "success": True,
            "loan_number": loan_number,
            "principal": principal,
            "interest_posted": interest,
            "next_interest_date": next_date.strftime("%Y-%m-%d")
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@interest_bp.route("/interest-posting-list", methods=["GET"])
def interest_posting_list():
    try:
        date = request.args.get("date")
        if not date:
            return jsonify({"success": False, "message": "date is required (YYYY-MM-DD)"}), 400

        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            return jsonify({"success": False, "message": "Invalid date format. Use YYYY-MM-DD"}), 400

        loan_coll = get_loan_collection()
        loans = loan_coll.find({"loan_status": "DISBURSED", "next_interest_date": date})

        data = []
        for loan in loans:
            data.append({
                "loan_number": loan.get("loan_number"),
                "customer_id": loan.get("customer_id"),
                "loan_amount": loan.get("loan_amount"),
                "outstanding_principal": loan.get("outstanding_principal"),
                "interest_rate": loan.get("interest_rate"),
                "frequency": loan.get("frequency"),
                "next_interest_date": loan.get("next_interest_date"),
                "interest_outstanding": loan.get("interest_outstanding", 0)
            })

        return jsonify({
            "success": True,
            "date": date,
            "total_loans": len(data),
            "data": data
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@interest_bp.route("/interest-posting-batch", methods=["POST"])
def interest_posting_batch():
    try:
        data = request.get_json() or {}
        posting_date = data.get("posting_date")
        if not posting_date:
            return jsonify({"success": False, "message": "posting_date is required (YYYY-MM-DD)"}), 400

        try:
            post_date = datetime.strptime(posting_date, "%Y-%m-%d")
        except Exception:
            return jsonify({"success": False, "message": "Invalid posting_date format"}), 400

        loan_coll = get_loan_collection()
        interest_coll = get_interest_collection()

        loans = loan_coll.find({"loan_status": "DISBURSED", "next_interest_date": posting_date})

        total_processed = 0
        total_interest = 0.0
        processed_loans = []

        for loan in loans:
            principal = float(loan.get("outstanding_principal", 0))
            annual_rate = float(loan.get("interest_rate", 0))
            frequency = loan.get("frequency", "monthly").lower()

            if frequency == "daily":
                interest = principal * annual_rate / (365 * 100)
                next_date = post_date + timedelta(days=1)
            elif frequency == "weekly":
                interest = principal * annual_rate / (52 * 100)
                next_date = post_date + timedelta(days=7)
            elif frequency == "monthly":
                interest = principal * annual_rate / (12 * 100)
                next_date = post_date + relativedelta(months=1)
            else:
                continue

            interest = round(interest, 2)

            already_posted = interest_coll.find_one({
                "loan_number": loan["loan_number"],
                "posting_date": post_date
            })
            if already_posted:
                continue

            interest_coll.insert_one({
                "loan_id": loan["_id"],
                "loan_number": loan["loan_number"],
                "customer_id": loan["customer_id"],
                "posting_date": post_date,
                "principal": principal,
                "interest_rate": annual_rate,
                "interest_amount": interest,
                "frequency": frequency,
                "status": "UNPAID",
                "created_at": datetime.utcnow()
            })

            loan_coll.update_one(
                {"_id": loan["_id"]},
                {
                    "$inc": {"interest_outstanding": interest},
                    "$set": {
                        "next_interest_date": next_date.strftime("%Y-%m-%d"),
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            total_processed += 1
            total_interest += interest
            processed_loans.append({
                "loan_number": loan["loan_number"],
                "interest": interest,
                "next_interest_date": next_date.strftime("%Y-%m-%d")
            })

        return jsonify({
            "success": True,
            "posting_date": posting_date,
            "total_processed": total_processed,
            "total_interest_posted": round(total_interest, 2),
            "data": processed_loans
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
