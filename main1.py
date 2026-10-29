"""Run MoneyPilot with: python3 main.py"""

from copy import deepcopy
from datetime import date
from pathlib import Path

from finance import (affordability, calculate_balance, category_spending,
                     monthly_totals, project_balance, runway)
from storage import load_data, save_data
from transactions import (add_record, find_record, filter_history, format_money,
                          new_state, parse_money, remove_record, update_record)


DEFAULT_FILE = Path(__file__).resolve().with_name("moneypilot.json")
MENU = """
+====================================+
|              MONEYPILOT            |
|====================================|
|  1. Manage actual transactions     |
|  2. Balance, spending, and runway  |
|  3. Check a purchase               |
|  4. Manage monthly plans           |
|  5. Filter actual history          |
|  6. Six-month projection           |
|  7. Opening balance and reserve    |
|  8. Save JSON                      |
|  9. Load JSON                      |
|  0. Exit                           |
+====================================+
"""

def ask_list(prompt, choices, default=""):
    if len(choices) != 0:
        prompt += f" no choices"
    for i, choice in enumerate(choices, 1):
        print(f"  {i}) {choice}")
        
    while True:
        if default != "":
            prompt = f"[{default}]"
        answer = input(f"Enter number (1-{len(choices)})[{default}]: ").strip()
        if answer.isdigit() and 1 <= int(answer) <= len(choices):
            return choices[int(answer) - 1]
        if answer == "" and default != "":
            return default
        print("❌ Invalid selection. Please try again.")
    return choices[answer]


def ask(prompt, default=""):
    """A blank answer keeps the displayed default."""
    if default != "":
        prompt += f" [{default}]"
    answer = input(prompt + ": ").strip()
    if answer == "":
        return default
    return answer


def read_record(section, old=None):
    if old is None:
        old = {"kind": "", "amount_cents": 0, "category": "",
               "date": date.today().isoformat(), "note": ""}
    amount_text = format_money(old["amount_cents"]).replace(",", "")
    kind = ask_list("Type: income or expense",["income", "expense"],old["kind"]).casefold()
    amount = parse_money(ask("Amount in baht", amount_text))
    if kind == "income":
        cat = ["salary","bonus","commission","wage","tip","other"] 
    else:
        cat = ["dining","transportation","utility","water","clothing","grocery","health care","entertainment","debt payments","other"]

    category = ask_list("Category",cat,old["category"])
    values = {"kind": kind, "amount_cents": amount, "category": category}
    if section == "transactions":
        values["date"] = ask("Completed date YYYY-MM-DD", old["date"])
        note = ask("Note, optional; a dot clears it", old["note"])
        values["note"] = "" if note == "." else note
    return values


def show_records(records):
    if not records:
        print("No matching records.")
    else:
        template = "| {:^3} | {:^7} | {:^15} | {:^14}  | {:^10} | {:^20} |"
        template2= "| {:>3} | {:<7} | {:<15} | {:>10} baht"
        note = "| {:<20} |"
        print(template.format("ID","Kind","Category","Amount","Date","Note"))
    for record in records:
        amount = format_money(record["amount_cents"])

        line = template2.format( record['id'] , record['kind'] , record['category'],amount)
        if "date" in record:
            line += f" | {record['date']} "
        else:
            line += " per future month"
        line += note.format(record['note'])
        print(line)


def manage_records(state, section):
    print("\nEditing:", section)
    if section == "plans":
        print("Each plan is a whole monthly total. It does not record a payment.")
    while True:
        print("\n1 Add | 2 View | 3 Update | 4 Remove | 0 Back")
        choice = ask("Choose")
        try:
            if choice == "1":
                values = read_record(section)
                record = add_record(state, section, values)
                print(f"Added record {record['id']}.")
            elif choice == "2":
                show_records(state[section])
            elif choice == "3":
                record_id = int(ask("ID to update"))
                old = find_record(state, section, record_id)
                values = read_record(section, old)
                update_record(state, section, record_id, values)
                print("Record updated.")
            elif choice == "4":
                record_id = int(ask("ID to remove"))
                remove_record(state, section, record_id)
                print("Record removed.")
            elif choice == "0":
                return
            else:
                print("Invalid choice. Use 0 to 4.")
        except ValueError as error:
            print("Action canceled:", error)


def show_spending(records):
    totals = category_spending(records)
    if not totals:
        print("No actual expenses in this selection.")
    for category, amount in totals.items():
        print(f"  {category}: {format_money(amount)} baht")


def show_summary(state):
    print("Actual balance:", format_money(calculate_balance(state)), "baht")
    print("Protected reserve:", format_money(state["settings"]["reserve_cents"]), "baht")
    print("Actual spending by category:")
    show_spending(state["transactions"])
    totals = monthly_totals(state)
    print("Planned monthly income:", format_money(totals["income_cents"]), "baht")
    print("Planned monthly expenses:", format_money(totals["expense_cents"]), "baht")
    months = runway(state)
    if months is None:
        print("Runway: no depletion under this plan.")
    else:
        print(f"Approximate time to the reserve boundary: {months:.2f} months.")
    if not state["plans"]:
        print("No monthly plans. Forecast assumes zero future flows.")


def main():
    state = new_state()
    saved_state = deepcopy(state)  # A separate snapshot detects unsaved changes.
    print("MoneyPilot | baht | Actual history and separate monthly forecasts")
    print("Save and load are explicit. Nothing is auto-saved.")
    try:
        while True:
            print(MENU)
            choice = ask("Choose")
            try:
                match choice:
                    case "1":
                        manage_records(state, "transactions")
                    case "2":
                        show_summary(state)
                    case "3":
                        price = parse_money(ask("One-time purchase price in baht"))
                        result = affordability(state, price)
                        if result["affordable"]:
                            print("PASS: reserve survives now and six monthly closing balances.")
                        elif result["failed_month"] == 0:
                            print("FAIL: below reserve immediately after the purchase.")
                        else:
                            print("FAIL: below reserve in projected month", result["failed_month"])
                        if not state["plans"]:
                            print("No monthly plans. Forecast assumes zero future flows.")
                        print("Simulation only. No purchase was recorded.")
                    case "4":
                        manage_records(state, "plans")
                    case "5":
                        print("Blank filters mean any value. Dates include both endpoints.")
                        kind = ask("Type: income/expense or blank").casefold()
                        category = ask("Exact category or blank")
                        start = ask("From YYYY-MM-DD or blank")
                        end = ask("To YYYY-MM-DD or blank")
                        matches = filter_history(state, kind, category, start, end)
                        show_records(matches)
                        show_spending(matches)
                    case "6":
                        print("Six simulated future months, without calendar due dates.")
                        print("Starting actual balance:", format_money(calculate_balance(state)), "baht")
                        if not state["plans"]:
                            print("No monthly plans. Forecast assumes zero future flows.")
                        for row in project_balance(state):
                            status = "OK"
                            if row["balance_cents"] < state["settings"]["reserve_cents"]:
                                status = "BELOW RESERVE"
                            print(f"Month {row['month']}: {format_money(row['balance_cents'])} baht | {status}")
                        print("Forecast only. Actual history is unchanged.")
                    case "7":
                        print("Opening balance is cash BEFORE every transaction in this ledger.")
                        print("Reserve is a threshold, not an extra expense.")
                        opening = parse_money(ask("Opening balance in baht"), allow_zero=True)
                        reserve = parse_money(ask("Protected reserve in baht"), allow_zero=True)
                        state["settings"] = {"opening_balance_cents": opening, "reserve_cents": reserve}
                        print("Settings updated.")
                    case "8":
                        path = Path(ask("Save file", str(DEFAULT_FILE))).expanduser()
                        if path.exists() and ask("Overwrite this file? y/n").lower() != "y":
                            print("Save canceled.")
                            continue
                        save_data(state, path)
                        saved_state = deepcopy(state)
                        print("Saved JSON:", path)
                    case "9":
                        path = ask("Load file", str(DEFAULT_FILE))
                        loaded = load_data(path)
                        if state != saved_state and ask("Type LOAD to discard unsaved changes") != "LOAD":
                            print("Load canceled. Session kept.")
                            continue
                        state = loaded
                        saved_state = deepcopy(state)
                        print("Loaded JSON:", path)
                    case "0":
                        if state != saved_state and ask("Exit without saving? y/n").lower() != "y":
                            print("Exit canceled. Use option 8 to save.")
                            continue
                        print("Goodbye!")
                        return
                    case _:
                        print("Invalid choice. Use 0 to 9.")
            except (ValueError, OSError) as error:
                print("Action canceled:", error)
    except (EOFError, KeyboardInterrupt):
        print("\nInput ended. Goodbye!")
        if state != saved_state:
            print("Unsaved changes were not written to disk.")


if __name__ == "__main__":
    main()
