from math import pow

def get_periods_per_year(frequency: str) -> int:
    """Return the number of payment periods per year based on frequency."""
    frequency = frequency.lower()
    mapping = {
        "daily": 365,
        "weekly": 52,
        "fortnightly": 26,
        "monthly": 12
    }
    if frequency not in mapping:
        raise ValueError("Frequency must be daily, weekly, fortnightly or monthly")
    return mapping[frequency]

def calculate_loan_schedule(principal: float, annual_rate: float, tenure: int, frequency: str = "monthly", interest_type: str = "reducing"):
    """
    Calculate the loan amortization schedule, installment amount, and interest totals.
    Supports 'reducing' balance and 'flat' interest calculations.
    """
    periods_per_year = get_periods_per_year(frequency)
    period_rate = annual_rate / (periods_per_year * 100)
    schedule = []

    if interest_type == "reducing":
        if period_rate == 0:
            installment = principal / tenure
        else:
            installment = (
                principal * period_rate * pow((1 + period_rate), tenure)
            ) / (pow((1 + period_rate), tenure) - 1)

        total_payment = installment * tenure
        total_interest = total_payment - principal
        balance = principal

        for i in range(1, tenure + 1):
            interest = balance * period_rate
            principal_paid = installment - interest

            if i == tenure:
                principal_paid = balance
                installment = principal_paid + interest

            balance -= principal_paid
            schedule.append({
                "period": i,
                "installment": round(installment),
                "principal": round(principal_paid),
                "interest": round(interest),
                "balance": round(max(balance, 0))
            })

    elif interest_type == "flat":
        total_interest = principal * period_rate * tenure
        total_payment = principal + total_interest
        installment = total_payment / tenure
        principal_paid = principal / tenure
        interest_each = total_interest / tenure
        balance = principal

        for i in range(1, tenure + 1):
            balance -= principal_paid
            schedule.append({
                "period": i,
                "installment": round(installment),
                "principal": round(principal_paid),
                "interest": round(interest_each),
                "balance": round(max(balance, 0))
            })
    else:
        raise ValueError("Interest type must be flat or reducing")

    return {
        "loan_amount": round(principal),
        "interest_rate": annual_rate,
        "frequency": frequency,
        "interest_type": interest_type,
        "tenure": tenure,
        "installment": round(installment),
        "total_interest": round(total_interest),
        "total_payment": round(total_payment),
        "schedule": schedule
    }
