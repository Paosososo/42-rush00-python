"""Run MoneyPilot with: python3 main.py"""

from copy import deepcopy
from datetime import date
from pathlib import Path

from finance import (affordability, calculate_balance, category_spending,
                     monthly_totals, project_balance, runway)
from storage import load_data, load_or_create_data, save_data
from transactions import (add_record, find_record, filter_history, format_money,
                          check_reserve, initialize_account, parse_money,
                          remove_record, update_record)


DEFAULT_FILE = Path(__file__).resolve().with_name("moneypilot.json")
MENU = """
+====================================+
|  💰          MONEYPILOT            ||
|====================================||
|  1. Manage actual transactions     ||
|  2. Balance, spending, and runway  ||
|  3. Check a purchase               ||
|  4. Manage monthly plans           ||
|  5. Filter actual history          ||
|  6. Six-month projection           ||
|  7. Change reserve                 ||
|  8. Export JSON backup             ||
|  9. Import JSON backup             ||
|  0. Exit                           ||
+====================================++
"""

def ask_list(prompt, choices, default=""):
    print(prompt)

    for number, choice in enumerate(choices, 1):
        print(f"  {number}) {choice}")

    while True:
        answer = input(
            f"Enter number (1-{len(choices)})[{default}]: "
        ).strip()

        if answer == "" and default != "":
            return default

        try:
            selected_number = int(answer)
        except ValueError:
            print("Please enter a number.")
            continue

        if 1 <= selected_number <= len(choices):
            return choices[selected_number - 1]

        print("Invalid selection. Please try again.")


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
        cat = ["salary","bonus","commission","wage","tip","dividend","cryto","other"] 
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
        template = "| {:^3} | {:^7} | {:^15} | {:^18}  | {:^10} | {:^30} |"
        template2= "| {:>3} | {:<7} | {:<15} | {:>14} "
        note = "| {:<30} |"
        if "date" in records[0]:
            print(template.format("ID","Kind","Category","Amount","Date","Note"))
        else:
            print(template2.format("ID","Kind","Category","Amount"))
    for record in records:
        amount = format_money(record["amount_cents"])

        line = template2.format( record['id'] , record['kind'] , record['category'],amount)
        line += "baht"
        if "date" in record:
            line += f" | {record['date']} "
            line += note.format(record['note'])
        else:
            line += " per future month"

        print(line)


def auto_save(state, saved_state, data_file):
    """Remember a change as saved only after the JSON write succeeds."""
    try:
        save_data(state, data_file)
    except ValueError as error:
        print("Automatic save failed:", error)
        print("The change is still in this session, but has NOT been saved.")
        return

    snapshot = deepcopy(state)
    saved_state.clear()
    saved_state.update(snapshot)
    print("Saved automatically.")


def manage_records(state, section, saved_state, data_file):
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
                auto_save(state, saved_state, data_file)
            elif choice == "2":
                show_records(state[section])
            elif choice == "3":
                record_id = int(ask("ID to update"))
                old = find_record(state, section, record_id)
                values = read_record(section, old)
                update_record(state, section, record_id, values)
                print("Record updated.")
                auto_save(state, saved_state, data_file)
            elif choice == "4":
                record_id = int(ask("ID to remove"))
                remove_record(state, section, record_id)
                print("Record removed.")
                auto_save(state, saved_state, data_file)
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
    input("\n (Please Press Enter to exit to main menu)")


def first_time_setup(state, data_file):
    """Ask for opening cash once and save only a fully validated setup."""
    print("First-time setup")
    print("Opening balance is cash BEFORE every transaction in this ledger.")

    while True:
        try:
            opening_text = ask("Opening balance in baht")
            opening = parse_money(opening_text, allow_zero=True)
            break
        except ValueError as error:
            print("Invalid opening balance:", error)

    while True:
        try:
            reserve_text = ask("Protected reserve in baht")
            reserve = parse_money(reserve_text, allow_zero=True)
            check_reserve(reserve, opening)
            break
        except ValueError as error:
            print("Invalid reserve:", error)

    # Keep the original session intact if the initial save fails.
    prepared = deepcopy(state)
    initialize_account(prepared, opening, reserve)
    save_data(prepared, data_file)
    print("Opening balance saved. Setup will not be requested again.")
    return prepared


def change_reserve(state, saved_state, data_file):
    """Change reserve against today's balance without editing opening cash."""
    balance = calculate_balance(state)
    balance_text = format_money(balance)
    print("Current balance:", balance_text, "baht")
    print("Opening balance has already been set and stays unchanged.")

    old_reserve = state["settings"]["reserve_cents"]
    default_text = format_money(old_reserve).replace(",", "")
    reserve_text = ask("New reserve in baht", default_text)
    reserve = parse_money(reserve_text, allow_zero=True)
    check_reserve(reserve, balance)

    state["settings"]["reserve_cents"] = reserve
    print("Reserve updated.")
    auto_save(state, saved_state, data_file)
    input("\n (Please Press Enter to exit to main menu)")


def main(data_file=None):
    if data_file is None:
        data_file = DEFAULT_FILE
    data_file = Path(data_file).expanduser()

    print("MoneyPilot | baht | Actual history and separate monthly forecasts")
    try:
        state = load_or_create_data(data_file)
        if not state["setup_complete"]:
            state = first_time_setup(state, data_file)
    except (EOFError, KeyboardInterrupt):
        print("\nSetup was not completed. Existing saved data was not replaced.")
        return
    except (ValueError, OSError) as error:
        print("Cannot open or initialize the data file:", error)
        print("Existing saved data was not replaced.")
        return

    saved_state = deepcopy(state)
    print("Data file:", data_file)
    print("Saved data loads on startup. Changes are saved automatically.")
    try:
        while True:
            print(MENU)
            choice = ask("Choose")
            try:
                match choice:
                    case "1":
                        manage_records(state, "transactions", saved_state, data_file)
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
                        input("\n (Please Press Enter to exit to main menu)")

                    case "4":
                        manage_records(state, "plans", saved_state, data_file)
                    case "5":
                        print("Blank filters mean any value. Dates include both endpoints.")
                        kind = ask("Type: income/expense or blank").casefold()
                        category = ask("Exact category or blank")
                        start = ask("From YYYY-MM-DD or blank")
                        end = ask("To YYYY-MM-DD or blank")
                        matches = filter_history(state, kind, category, start, end)
                        show_records(matches)
                        show_spending(matches)
                        input("\n (Please Press Enter to exit to main menu)")
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
                        input("\n (Please Press Enter to exit to main menu)")
                    case "7":
                        change_reserve(state, saved_state, data_file)
                    case "8":
                        backup_file = data_file.with_name("moneypilot_backup.json")
                        path = Path(ask("Export file", str(backup_file))).expanduser()
                        if path.exists() and ask("Overwrite this file? y/n").lower() != "y":
                            print("Save canceled.")
                            continue
                        save_data(state, path)
                        print("Saved JSON:", path)
                    case "9":
                        backup_file = data_file.with_name("moneypilot_backup.json")
                        path = ask("Import file", str(backup_file))
                        loaded = load_data(path)
                        if not loaded["setup_complete"]:
                            raise ValueError("That backup has no completed account setup.")
                        if ask("Type LOAD to overwrite the current saved data") != "LOAD":
                            print("Load canceled. Session kept.")
                            continue
                        # Write the replacement before changing the live session.
                        save_data(loaded, data_file)
                        state = loaded
                        saved_state = deepcopy(state)
                        print("Loaded JSON:", path)
                    case "0":
                        if state != saved_state:
                            auto_save(state, saved_state, data_file)
                            if state != saved_state:
                                answer = ask("Exit without saving? y/n").lower()
                                if answer != "y":
                                    print("Exit canceled. Your unsaved changes are still here.")
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
            auto_save(state, saved_state, data_file)
        if state != saved_state:
            print("Unsaved changes were not written to disk.")


if __name__ == "__main__":
    main()
