"""Manage records in baht, with money stored as integer satang.

Existing _cents field names are kept so saved JSON files stay compatible.
"""

from datetime import date


MAX_CENTS = 100_000_000_000  # Satang; maximum entered amount: 1 billion baht.


def new_state():
    """Create the empty session used when there is no saved data file."""

    return {
        "schema_version": 2,
        "setup_complete": False,
        "settings": {"opening_balance_cents": 0, "reserve_cents": 0},
        "transactions": [],  # Completed payments.
        "plans": [],         # Future monthly totals, not completed payments.
        "next_transaction_id": 1,
        "next_plan_id": 1,
    }


def check_amount(satang, allow_zero=False):
    """Reject an amount that cannot be used by the money calculations."""
    # An actual integer is required. True, False, and decimal numbers are rejected.
    if type(satang) is not int:
        raise ValueError("Amount must be an integer number of satang.")

    if satang < 0:
        raise ValueError("Amount cannot be negative.")

    if satang == 0 and not allow_zero:
        raise ValueError("Amount must be greater than zero.")

    if satang > MAX_CENTS:
        raise ValueError("Amount is too large.")


def parse_money(text, allow_zero=False):
    """Convert '12.50' baht into 1250 satang without using a float."""
    if not isinstance(text, str):
        raise ValueError("Enter an amount such as 12.50.")

    text = text.strip()

    if len(text) > 20:
        raise ValueError("Amount is too long.")

    if not text.isascii():
        raise ValueError("Use digits from 0 to 9.")

    parts = text.split(".")

    if len(parts) > 2:
        raise ValueError("Use only one decimal point.")

    baht_text = parts[0]

    if not baht_text.isdigit():
        raise ValueError("Baht must contain digits only.")

    satang_text = "00"

    if len(parts) == 2:
        satang_text = parts[1]

        if not satang_text.isdigit():
            raise ValueError("Enter digits after the decimal point.")

        if len(satang_text) > 2:
            raise ValueError("Use at most two decimal places.")

        if len(satang_text) == 1:
            satang_text = satang_text + "0"

    baht = int(baht_text)
    remaining_satang = int(satang_text)

    total_satang = baht * 100 + remaining_satang

    check_amount(total_satang, allow_zero)

    return total_satang

def format_money(satang):
    """Turn stored satang into readable baht text, such as '1,250.50'."""
    sign = ""
    if satang < 0:
        sign = "-"
        satang = abs(satang)

    baht = satang // 100
    remaining_satang = satang % 100

    return f"{sign}{baht:,}.{remaining_satang:02d}"


def check_reserve(reserve, balance):
    """Check a reserve when it is first set or changed by the user."""
    check_amount(reserve, allow_zero=True)

    if type(balance) is not int:
        raise ValueError("Balance must be an integer number of satang.")

    if reserve > balance:
        maximum = format_money(balance)
        raise ValueError(f"Reserve cannot exceed the current balance of {maximum} baht.")


def initialize_account(state, opening_balance, reserve):
    """Set opening cash once. A zero opening balance still completes setup."""
    validate_state(state)

    if state["setup_complete"]:
        raise ValueError("Opening balance has already been set.")

    check_amount(opening_balance, allow_zero=True)
    check_reserve(reserve, opening_balance)

    # Change the state only after both amounts pass their checks.
    state["settings"] = {
        "opening_balance_cents": opening_balance,
        "reserve_cents": reserve,
    }
    state["setup_complete"] = True


from datetime import date


def check_date(text, allow_future=False):
    """Require a real YYYY-MM-DD date and normally reject future payments."""
    if not isinstance(text, str):
        raise ValueError("Date must be text.")

    try:
        entered_date = date.fromisoformat(text)
    except ValueError:
        raise ValueError("Enter a real date, such as 2026-10-29.")

    formatted_date = entered_date.isoformat()

    if text != formatted_date:
        raise ValueError("Use YYYY-MM-DD format.")

    if not allow_future:
        today = date.today()

        if entered_date > today:
            raise ValueError("The payment date cannot be in the future.")


def clean_record(values, section):
    """Check all proposed fields before adding or changing a stored record."""
    if section not in ["transactions", "plans"]:
        raise ValueError("Unknown record list.")

    if type(values) is not dict:
        raise ValueError("Record must be a dictionary.")

    required_fields = ["kind", "amount_cents", "category"]

    if section == "transactions":
        required_fields.append("date")
        required_fields.append("note")

    # Check field names with ordinary loops instead of comparing sets.
    for field in required_fields:
        if field not in values:
            raise ValueError(f"Record is missing the {field} field.")

    for field in values:
        if field not in required_fields:
            raise ValueError(f"Record has an unexpected field: {field}.")

    # Clean a copy so a failed check cannot partly change the user's input.
    record = values.copy()

    if record["kind"] not in ["income", "expense"]:
        raise ValueError("Type must be income or expense.")

    check_amount(record["amount_cents"])

    category = record["category"]

    if not isinstance(category, str):
        raise ValueError("Category must be text.")

    category = category.strip()
    category = category.casefold()

    if category == "":
        raise ValueError("Category cannot be empty.")

    if len(category) > 40:
        raise ValueError("Category cannot exceed 40 characters.")

    if not category.isprintable():
        raise ValueError("Category cannot contain control characters.")

    record["category"] = category

    # Only completed transactions have a payment date and a note.
    if section == "transactions":
        check_date(record["date"])
        note = record["note"]

        if not isinstance(note, str):
            raise ValueError("Note must be text.")

        if len(note) > 200:
            raise ValueError("Note cannot exceed 200 characters.")

        note = note.strip()

        if note != "":
            if not note.isprintable():
                raise ValueError("Note cannot contain control characters.")

        record["note"] = note

    return record


def find_record(state, section, record_id):
    """Search the selected list and return the stored record with this ID."""
    if section not in ["transactions", "plans"]:
        raise ValueError("Unknown record list.")

    if type(record_id) is not int:
        raise ValueError("ID must be a whole number.")

    if record_id <= 0:
        raise ValueError("ID must be positive.")

    for record in state[section]:
        if record["id"] == record_id:
            return record

    raise ValueError(f"No record with ID {record_id} in {section}.")


def check_duplicate_plan(state, values, ignore_id=0):
    """Allow only one monthly total for each income/expense category."""
    for plan in state["plans"]:
        # An update must not treat the record being edited as its own duplicate.
        if plan["id"] == ignore_id:
            continue

        if plan["kind"] != values["kind"]:
            continue

        if plan["category"] != values["category"]:
            continue

        raise ValueError("That monthly type/category exists. Update it instead.")


def add_record(state, section, values):
    """Validate a record, assign its ID, and add it to the selected list."""
    record = clean_record(values, section)

    if section == "plans":
        check_duplicate_plan(state, record)
        counter_name = "next_plan_id"
    else:
        counter_name = "next_transaction_id"

    record_id = state[counter_name]
    record["id"] = record_id
    state[section].append(record)
    state[counter_name] = record_id + 1

    # A returned copy cannot accidentally change the stored record.
    return record.copy()


def update_record(state, section, record_id, values):
    """Replace editable fields only after every proposed value passes checks."""
    record = find_record(state, section, record_id)
    replacement = clean_record(values, section)

    if section == "plans":
        check_duplicate_plan(state, replacement, ignore_id=record_id)

    # The replacement has no ID field, so the existing ID stays unchanged.
    for field in replacement:
        record[field] = replacement[field]


def remove_record(state, section, record_id):
    """Find and remove a record without moving the next-ID counter backward."""
    record = find_record(state, section, record_id)
    state[section].remove(record)


def filter_history(state, kind="", category="", start="", end=""):
    """Collect actual transactions that pass every nonempty filter."""
    if kind != "":
        if kind not in ["income", "expense"]:
            raise ValueError("Filter type must be income or expense.")

    category = category.strip()
    category = category.casefold()

    if start != "":
        check_date(start, allow_future=True)

    if end != "":
        check_date(end, allow_future=True)

    if start != "" and end != "":
        if start > end:
            raise ValueError("Start date must not be after end date.")

    matches = []

    for record in state["transactions"]:
        if kind != "":
            if record["kind"] != kind:
                continue

        if category != "":
            if record["category"] != category:
                continue

        # Valid YYYY-MM-DD strings sort in date order. Both endpoints are included.
        if start != "":
            if record["date"] < start:
                continue

        if end != "":
            if record["date"] > end:
                continue

        matching_record = record.copy()
        matches.append(matching_record)

    return matches


def validate_state(state):
    """Check a whole saved session before allowing the app to use it."""
    if type(state) is not dict:
        raise ValueError("Not a MoneyPilot data file.")

    expected_state = new_state()

    for field in expected_state:
        if field not in state:
            raise ValueError(f"Data file is missing the {field} field.")

    for field in state:
        if field not in expected_state:
            raise ValueError(f"Data file has an unexpected field: {field}.")

    if type(state["schema_version"]) is not int:
        raise ValueError("File version must be a whole number.")

    if state["schema_version"] != 2:
        raise ValueError("Unsupported file version.")

    if type(state["setup_complete"]) is not bool:
        raise ValueError("Setup status must be true or false.")

    settings = state["settings"]

    if type(settings) is not dict:
        raise ValueError("Settings must be a dictionary.")

    setting_names = ["opening_balance_cents", "reserve_cents"]

    for field in setting_names:
        if field not in settings:
            raise ValueError(f"Settings are missing the {field} field.")

    for field in settings:
        if field not in setting_names:
            raise ValueError(f"Settings have an unexpected field: {field}.")

    check_amount(settings["opening_balance_cents"], allow_zero=True)
    check_amount(settings["reserve_cents"], allow_zero=True)

    for section in ["transactions", "plans"]:
        if section == "transactions":
            counter_name = "next_transaction_id"
        else:
            counter_name = "next_plan_id"

        records = state[section]

        if type(records) is not list:
            raise ValueError("Records must be stored in lists.")

        used_ids = []
        used_plans = []
        largest_id = 0

        for record in records:
            if type(record) is not dict:
                raise ValueError("Each record must be a dictionary.")

            if "id" not in record:
                raise ValueError("Record is missing its ID.")

            record_id = record["id"]

            if type(record_id) is not int:
                raise ValueError("Record IDs must be whole numbers.")

            if record_id <= 0:
                raise ValueError("Record IDs must be positive.")

            if record_id in used_ids:
                raise ValueError("Record IDs cannot be duplicated in the same list.")

            used_ids.append(record_id)

            if record_id > largest_id:
                largest_id = record_id

            # The ID was checked above. Check the editable fields separately.
            values = record.copy()
            del values["id"]
            cleaned_values = clean_record(values, section)

            if cleaned_values != values:
                raise ValueError("Stored text must already be trimmed and normalized.")

            if section == "plans":
                plan_details = [values["kind"], values["category"]]

                if plan_details in used_plans:
                    raise ValueError("Duplicate monthly type/category.")

                used_plans.append(plan_details)

        next_id = state[counter_name]

        if type(next_id) is not int:
            raise ValueError("The next record ID must be a whole number.")

        if next_id <= largest_id:
            raise ValueError("The next record ID must exceed all existing IDs.")

    # An unfinished setup must not contain money or history that could be reset.
    if not state["setup_complete"]:
        if settings["opening_balance_cents"] != 0:
            raise ValueError("An unfinished setup cannot contain an opening balance.")
        if settings["reserve_cents"] != 0:
            raise ValueError("An unfinished setup cannot contain a reserve.")
        if len(state["transactions"]) != 0:
            raise ValueError("An unfinished setup cannot contain transactions.")
        if len(state["plans"]) != 0:
            raise ValueError("An unfinished setup cannot contain monthly plans.")
        if state["next_transaction_id"] != 1:
            raise ValueError("An unfinished setup cannot contain a used transaction counter.")
        if state["next_plan_id"] != 1:
            raise ValueError("An unfinished setup cannot contain a used plan counter.")
