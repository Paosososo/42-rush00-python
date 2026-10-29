"""Calculations only. None of these functions changes stored records."""

from transactions import check_amount


def calculate_balance(state):
    balance = state["settings"]["opening_balance_cents"]
    for record in state["transactions"]:
        if record["kind"] == "income":
            balance += record["amount_cents"]
        else:
            balance -= record["amount_cents"]
    return balance


def category_spending(records):
    totals = {}
    for record in records:
        if record["kind"] == "expense":
            category = record["category"]
            if category not in totals:
                totals[category] = 0
            totals[category] += record["amount_cents"]
    return totals


def monthly_totals(state):
    totals = {"income_cents": 0, "expense_cents": 0}
    for plan in state["plans"]:
        if plan["kind"] == "income":
            totals["income_cents"] += plan["amount_cents"]
        else:
            totals["expense_cents"] += plan["amount_cents"]
    return totals


def runway(state):
    """Return months to the reserve boundary, or None for no depletion."""
    balance = calculate_balance(state)
    reserve = state["settings"]["reserve_cents"]
    totals = monthly_totals(state)
    burn = totals["expense_cents"] - totals["income_cents"]
    if balance < reserve:
        return 0.0
    elif burn <= 0:
        return None
    else:
        return (balance - reserve) / burn


def project_balance(state, purchase_cents=0):
    """Apply each monthly total once in each of six future scenario months."""
    check_amount(purchase_cents, allow_zero=True)
    balance = calculate_balance(state) - purchase_cents
    totals = monthly_totals(state)
    rows = []
    for month in range(1, 7):
        balance += totals["income_cents"] - totals["expense_cents"]
        rows.append({"month": month, "balance_cents": balance})
    return rows


def affordability(state, price_cents):
    """Return the first reserve failure: 0 means now, 1..6 means future."""
    check_amount(price_cents)
    reserve = state["settings"]["reserve_cents"]
    if calculate_balance(state) - price_cents < reserve:
        return {"affordable": False, "failed_month": 0}
    for row in project_balance(state, price_cents):
        if row["balance_cents"] < reserve:
            return {"affordable": False, "failed_month": row["month"]}
    return {"affordable": True, "failed_month": None}
