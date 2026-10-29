"""Manage records in baht, with money stored as integer satang.

Existing _cents field names are kept so saved JSON files stay compatible.
"""

from datetime import date


MAX_CENTS = 100_000_000_000  # Satang; maximum entered amount: 1 billion baht.


def new_state():
    return {
        "schema_version": 1,
        "settings": {"opening_balance_cents": 0, "reserve_cents": 0},
        "transactions": [],  # Completed payments.
        "plans": [],         # Future monthly totals, not completed payments.
        "next_transaction_id": 1,
        "next_plan_id": 1,
    }


def check_amount(satang, allow_zero=False):
    minimum = 0 if allow_zero else 1
    if type(satang) is not int or satang < minimum or satang > MAX_CENTS:
        raise ValueError("Amount is outside the allowed range.")


def parse_money(text, allow_zero=False):
    """Convert '12.50' baht into 1250 satang without using a float."""
    if not isinstance(text, str):
        raise ValueError("Enter an amount such as 12.50.")
    text = text.strip()
    parts = text.split(".")
    if len(text) > 20 or len(parts) > 2 or not text.isascii():
        raise ValueError("Use digits and at most two decimal places.")
    whole = parts[0]
    fraction = "00"
    if len(parts) == 2:
        fraction = parts[1]
        if not fraction.isdigit() or len(fraction) > 2:
            raise ValueError("Use one or two digits after the decimal point.")
        if len(fraction) == 1:
            fraction += "0"
    if not whole.isdigit():
        raise ValueError("Use digits without commas, signs, or exponents.")
    satang = int(whole) * 100 + int(fraction)
    check_amount(satang, allow_zero)
    return satang


def format_money(satang):
    sign = "-" if satang < 0 else ""
    whole, fraction = divmod(abs(satang), 100)
    return f"{sign}{whole:,}.{fraction:02d}"


def check_date(text, allow_future=False):
    if not isinstance(text, str):
        raise ValueError("Use a real date in YYYY-MM-DD format.")
    try:
        day = date.fromisoformat(text)
    except ValueError:
        raise ValueError("Use a real date in YYYY-MM-DD format.") from None
    if day.isoformat() != text:
        raise ValueError("Use the full YYYY-MM-DD date format.")
    if not allow_future and day > date.today():
        raise ValueError("Actual history cannot contain a future payment.")


def clean_record(values, section):
    """Check all fields and return a new dictionary before changing data."""
    if section not in ("transactions", "plans"):
        raise ValueError("Unknown record list.")
    fields = ["kind", "amount_cents", "category"]
    if section == "transactions":
        fields += ["date", "note"]
    if type(values) is not dict or set(values) != set(fields):
        raise ValueError("Record has missing or unexpected fields.")
    record = values.copy()
    if record["kind"] not in ("income", "expense"):
        raise ValueError("Type must be income or expense.")
    check_amount(record["amount_cents"])
    category = record["category"]
    if not isinstance(category, str):
        raise ValueError("Category must be text.")
    category = category.strip().casefold()
    if not category or len(category) > 40 or not category.isprintable():
        raise ValueError("Category needs 1 to 40 printable characters.")
    record["category"] = category
    if section == "transactions":
        check_date(record["date"])
        note = record["note"]
        if not isinstance(note, str) or len(note) > 200:
            raise ValueError("Note must be text, at most 200 characters.")
        note = note.strip()
        if note and not note.isprintable():
            raise ValueError("Note cannot contain control characters.")
        record["note"] = note
    return record


def find_record(state, section, record_id):
    if section not in ("transactions", "plans"):
        raise ValueError("Unknown record list.")
    if type(record_id) is not int or record_id <= 0:
        raise ValueError("ID must be a positive whole number.")
    for record in state[section]:
        if record["id"] == record_id:
            return record
    raise ValueError(f"No record with ID {record_id} in {section}.")


def check_duplicate_plan(state, values, ignore_id=0):
    for plan in state["plans"]:
        if (plan["id"] != ignore_id and plan["kind"] == values["kind"]
                and plan["category"] == values["category"]):
            raise ValueError("That monthly type/category exists. Update it instead.")


def add_record(state, section, values):
    record = clean_record(values, section)
    if section == "plans":
        check_duplicate_plan(state, record)
        counter = "next_plan_id"
    else:
        counter = "next_transaction_id"
    record["id"] = state[counter]
    state[section].append(record)
    state[counter] += 1
    return record.copy()


def update_record(state, section, record_id, values):
    record = find_record(state, section, record_id)
    replacement = clean_record(values, section)
    if section == "plans":
        check_duplicate_plan(state, replacement, ignore_id=record_id)
    record.update(replacement)


def remove_record(state, section, record_id):
    record = find_record(state, section, record_id)
    state[section].remove(record)


def filter_history(state, kind="", category="", start="", end=""):
    if kind and kind not in ("income", "expense"):
        raise ValueError("Filter type must be income or expense.")
    category = category.strip().casefold()
    if start:
        check_date(start, allow_future=True)
    if end:
        check_date(end, allow_future=True)
    if start and end and start > end:
        raise ValueError("Start date must not be after end date.")
    matches = []
    for record in state["transactions"]:
        if kind and record["kind"] != kind:
            continue
        if category and record["category"] != category:
            continue
        if start and record["date"] < start:
            continue
        if end and record["date"] > end:
            continue
        matches.append(record.copy())
    return matches


def validate_state(state):
    """Reject broken JSON data before replacing the current session."""
    if type(state) is not dict or set(state) != set(new_state()):
        raise ValueError("Not a MoneyPilot data file.")
    if type(state["schema_version"]) is not int or state["schema_version"] != 1:
        raise ValueError("Unsupported file version.")
    settings = state["settings"]
    if type(settings) is not dict or set(settings) != {"opening_balance_cents", "reserve_cents"}:
        raise ValueError("Invalid settings.")
    check_amount(settings["opening_balance_cents"], allow_zero=True)
    check_amount(settings["reserve_cents"], allow_zero=True)
    for section, counter in (("transactions", "next_transaction_id"), ("plans", "next_plan_id")):
        if type(state[section]) is not list:
            raise ValueError("Records must be stored in lists.")
        used_ids = []
        used_plans = []
        for record in state[section]:
            if type(record) is not dict:
                raise ValueError("Each record must be a dictionary.")
            values = record.copy()
            record_id = values.pop("id", None)
            if type(record_id) is not int or record_id <= 0 or record_id in used_ids:
                raise ValueError("Record IDs must be unique positive integers.")
            used_ids.append(record_id)
            if clean_record(values, section) != values:
                raise ValueError("Stored text must already be trimmed and normalized.")
            if section == "plans":
                pair = (values["kind"], values["category"])
                if pair in used_plans:
                    raise ValueError("Duplicate monthly type/category.")
                used_plans.append(pair)
        if type(state[counter]) is not int or state[counter] <= max(used_ids, default=0):
            raise ValueError("Invalid next record ID.")
