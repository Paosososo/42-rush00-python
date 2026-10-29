"""Calculate results without changing actual history or monthly plans."""

from transactions import check_amount


def calculate_balance(state):
    """Start with opening cash, add actual income, and subtract actual expenses."""
    balance = state["settings"]["opening_balance_cents"]

    for record in state["transactions"]:
        amount_satang = record["amount_cents"]

        if record["kind"] == "income":
            balance = balance + amount_satang
        else:
            balance = balance - amount_satang

    # Monthly plans are not completed payments, so this function does not add them.
    return balance


def category_spending(records):
    """Add actual expenses into a dictionary, using categories as the keys."""
    totals = {}

    for record in records:
        if record["kind"] == "expense":
            category = record["category"]
            amount_satang = record["amount_cents"]

            if category not in totals:
                totals[category] = 0

            totals[category] = totals[category] + amount_satang

    return totals


def monthly_totals(state):
    """Calculate expected income and expenses for one future month."""
    income_satang = 0
    expenses_satang = 0

    for plan in state["plans"]:
        amount_satang = plan["amount_cents"]

        if plan["kind"] == "income":
            income_satang = income_satang + amount_satang
        else:
            expenses_satang = expenses_satang + amount_satang

    totals = {
        "income_cents": income_satang,
        "expense_cents": expenses_satang,
    }
    return totals


def runway(state):
    """Estimate months until cash reaches the protected reserve."""
    balance = calculate_balance(state)
    reserve = state["settings"]["reserve_cents"]
    totals = monthly_totals(state)
    monthly_income = totals["income_cents"]
    monthly_expenses = totals["expense_cents"]
    monthly_burn = monthly_expenses - monthly_income

    if balance < reserve:
        return 0.0

    # None means the plan does not use up cash. It also avoids division by zero.
    if monthly_burn <= 0:
        return None

    available_cash = balance - reserve
    months = available_cash / monthly_burn
    return months


def project_balance(state, purchase_cents=0):
    """Calculate six future monthly closing balances without recording payments."""
    check_amount(purchase_cents, allow_zero=True)

    # Count history once, then subtract the proposed one-time purchase once.
    balance = calculate_balance(state)
    balance = balance - purchase_cents

    totals = monthly_totals(state)
    monthly_income = totals["income_cents"]
    monthly_expenses = totals["expense_cents"]
    monthly_change = monthly_income - monthly_expenses
    rows = []

    for month in range(1, 7):
        balance = balance + monthly_change

        row = {
            "month": month,
            "balance_cents": balance,
        }
        rows.append(row)

    return rows


def affordability(state, price_cents):
    """Check whether a purchase protects the reserve now and for six months."""
    check_amount(price_cents)

    reserve = state["settings"]["reserve_cents"]
    current_balance = calculate_balance(state)
    after_purchase = current_balance - price_cents

    # Month zero means the purchase itself immediately breaks the reserve.
    if after_purchase < reserve:
        return {"affordable": False, "failed_month": 0}

    rows = project_balance(state, price_cents)

    for row in rows:
        future_balance = row["balance_cents"]

        if future_balance < reserve:
            failed_month = row["month"]
            return {"affordable": False, "failed_month": failed_month}

    return {"affordable": True, "failed_month": None}
