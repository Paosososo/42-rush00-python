# MoneyPilot

MoneyPilot is a Python terminal application for the 42 Bangkok Rush00 project.
It records actual income and expenses in baht, groups spending by category,
and uses a separate monthly plan to estimate future balances and check a
proposed purchase.

## Requirements and running

- Python 3.10 or later. The main menu uses [`match` and `case`](https://docs.python.org/3.10/reference/compound_stmts.html#the-match-statement).
- Python standard library only. No additional packages or accounts are needed.

From the repository folder:

```sh
python3 main.py
```

**Saving and loading are manual in this checkout.** Each run starts with an
empty session. Use option **9** to reopen saved data and option **8** to save
your changes before exiting.

## Main menu

| Choice | Action |
| --- | --- |
| 1 | Add, view, update, or remove actual transactions |
| 2 | Show actual balance, category spending, and reserve runway |
| 3 | Check a proposed one-time purchase |
| 4 | Add, view, update, or remove recurring monthly plans |
| 5 | Filter actual history by type, category, and date range |
| 6 | Show six projected monthly closing balances |
| 7 | Set opening balance and protected reserve |
| 8 | Save the current session as JSON |
| 9 | Load a saved JSON session |
| 0 | Exit |

Options 1 and 4 open a second menu:

```text
1 Add | 2 View | 3 Update | 4 Remove | 0 Back
```

When adding a record, select its type and category using the displayed
numbers. Type **1** selects income and type **2** selects expense. The category
choices depend on that type, for example salary for income and grocery for
expenses. Enter the amount in baht, such as `1250.50`, without commas or a
currency symbol.

Actual transactions also require a completed-payment date in `YYYY-MM-DD`
format and allow an optional note. When updating a record, a blank answer
keeps the displayed value. Enter a single dot to clear a note. Use the record's
ID when updating or removing it.

For option 5, enter the type as `income` or `expense` and the full category
name, for example `grocery`. Leave a filter blank to match any value. Both
date endpoints are included, and results remain in recorded order.

## Files

```text
42-rush00-python/
    main.py
    transactions.py
    finance.py
    storage.py
    README.md
    auteur
    moneypilot.json
```

| File | Responsibility |
| --- | --- |
| [main.py](main.py) | Terminal menus, numbered selections, user input, and printed results |
| [transactions.py](transactions.py) | Session structure, money/date validation, record management, and filters |
| [finance.py](finance.py) | Balance, category totals, monthly totals, runway, projection, and affordability |
| [storage.py](storage.py) | JSON validation, loading, and saving through a temporary file |
| [auteur](auteur) | The team's Intra login entries |
| `moneypilot.json` | Saved session data written through option 8 |

Keep the four Python modules together so their imports can find each other.

## How the money model works

### Actual transactions and opening balance

`state["transactions"]` stores payments that have already happened. Each
record is a dictionary with an ID, type, amount, category, date, and note.

The opening balance means cash **before all transactions included in the
ledger**. Actual balance is calculated as:

```text
actual balance = opening balance + recorded income - recorded expenses
```

Do not enter today's bank balance and also enter the same past payments.
Reconcile opening balance if you change which history is included. Actual
expenses may produce a negative balance because the ledger records what
happened rather than preventing an overdraft. Treat the tracked cash as one
combined pool; transfers within that pool are not additional income or expenses.

### Baht and satang

Users enter and see baht. Internally, money is stored as integer satang:

```text
12.50 baht  ->  1250 satang
```

Fields such as `amount_cents` and `reserve_cents` keep their existing names
for saved-file compatibility, but represent satang in this project. All money
totals use integers. The runway ratio uses a float because months can include
a fraction.

### Monthly plans and forecasts

`state["plans"]` stores expected future monthly totals. For example, an
expense plan of `2500` baht means 2,500 baht in **each** future scenario month.
It is not a daily amount or a total for the whole six-month projection.

Adding a plan does not change actual balance or create an actual payment.
The forecast counts recorded history once in its starting balance and applies
each monthly plan once per future period. A real payment belongs in actual
history once; its plan describes later future periods.

```text
monthly change = planned income - planned expenses
next balance = previous balance + monthly change
```

The projection repeats that calculation six times. These are scenario months,
not dated payment schedules. The model does not calculate the remaining days
of the current month, payment timing within a month, interest, inflation, or
future one-time costs. Without plans, future income and expenses are assumed
to be zero.

### Protected reserve and runway

The reserve is the minimum cash balance the user wants to protect. It is a
threshold, not an expense subtracted from the ledger or every forecast month.

```text
available cash = actual balance - reserve
monthly burn = planned expenses - planned income
runway in months = available cash / monthly burn
```

If actual balance is already below reserve, runway is zero. If reserve is
intact and monthly burn is zero or negative, the result is `None`, displayed
as no depletion under the entered plan.

### Purchase checks

Option 3 subtracts a proposed purchase once, then checks the remaining balance
immediately and at all six projected month endings. It passes only when every
checked balance is at least the reserve. Equality with reserve passes.

The result identifies an immediate failure or the first failed future month.
A purchase may fail even when there is enough money to pay its price today.
The simulation does not record a purchase. After a real purchase, add the
actual expense once through option 1.

Runway and purchase results depend on the entered monthly plan. They do not
establish that a bill due before payday can be paid within a particular month.

## Save and reopen data

1. Use option **8** and press Enter to save as `moneypilot.json` beside
   `main.py`, or enter another path. Existing parent directories are required.
2. Confirm before overwriting an existing file.
3. On a later run, use option **9** and press Enter to load that default file,
   or enter the path you used before.

Saving stores the settings, actual transactions, monthly plans, ID counters,
and file-format version. Loading replaces the session rather than appending
records. If the session has unsaved changes, type `LOAD` to confirm replacement.
A failed load leaves the current session available.

When exiting with unsaved changes, choose `n` to return to the menu and save
with option 8. Choosing `y` discards those unsaved changes. EOF and Ctrl+C exit
without automatically saving them.

Storage writes a complete temporary file before replacing an existing save.
The automatic-loading helper present in `storage.py` is not called by this
checkout's `main()`; startup does not restore the JSON file automatically.

## Validation and business rules

- Payment amounts, monthly totals, and purchase prices must be positive.
  Opening balance and reserve may be zero. Input allows at most two decimal
  places and up to 1,000,000,000.00 baht per entered amount.
- Actual payment dates must be real dates and cannot be in the future.
- A monthly type/category pair must be unique. Update the existing total
  instead of adding it twice, or remove it to stop that plan.
- A proposed purchase must preserve the reserve now and in all six future
  periods. Equal actual payments are allowed because both may have happened.

Record validation also checks categories, note lengths, field names, and IDs.
Saved data is checked for the expected structure, supported version, valid
amounts, unique IDs, valid counters, and duplicate plans. Menus report invalid
input, missing IDs, and file problems without treating the action as successful.

## Example workflow

These are fictional practice values. Start with an empty session.

1. Option 7: set opening balance to `10000` and reserve to `2000`.
2. Option 1, Add: select income, enter `2000`, select salary, and enter a past
   payment date and an optional note.
3. Add an expense of `500`, category grocery, then choose Back.
4. Option 2: actual balance is `11,500.00` baht and grocery spending is `500.00`.
5. Option 4: add monthly income of `1000` in salary and monthly expenses of
   `2500` in other, then choose Back.
6. Option 2: monthly burn is 1,500 baht and reserve runway is about 6.33 months.
7. Option 6: projected balances are 10,000; 8,500; 7,000; 5,500; 4,000; and
   2,500 baht.
8. Option 3: a `500` purchase passes because month 6 ends at reserve, 2,000 baht.
   A `600` purchase fails in month 6 at 1,900 baht. Neither check changes history.
9. Option 5: filter `expense` and `grocery`, with a date range covering the
   payment. Update and remove that record through option 1 to demonstrate CRUD.
10. Save with option 8. Exit, restart, and load with option 9 to restore the data.

## Checking the program

To check Python syntax from the repository folder:

```sh
python3 -m py_compile main.py transactions.py finance.py storage.py
```

This checks syntax rather than complete behavior. This checkout does not
include an automated test-suite file. A documentation smoke check using
Python 3.14.5 exercised all nine main options in an isolated copy, including
record CRUD, a plan update, filters, the example calculations, purchase checks,
and manual save/load across separate launches.

For a defense rehearsal, also demonstrate an invalid menu choice, an invalid
amount, a future payment date, a nonexistent ID, and a duplicate monthly plan.

## Rush00 concepts to explain

| Area | Examples in this project |
| --- | --- |
| Interactive menu | Main `match`/`case` menu, `input()`, `print()`, and Back/Exit actions |
| Lists and dictionaries | Session dictionary, two record lists, and record dictionaries |
| Conditional rules | Amount/date checks, unique plans, and reserve decisions |
| Loops | `while` menus and `for` loops over stored records and forecast periods |
| Functions | Separate modules, parameters, returned results, and reusable record operations |
| Data processing | Balance, category aggregation, filtering, monthly totals, and projections |
| Error handling | Invalid-input messages, missing-record checks, and JSON/file errors |
| Complete workflow | Add, inspect, edit, remove, calculate, save, and reopen records |

Both teammates should be able to explain the full application and demonstrate
its workflow. The current repository stores the application at its root.
For the course turn-in, arrange the required Python files, README, and `auteur`
inside the assignment's `rush/` directory. Keep the modules together and
confirm that `auteur` contains both real Intra logins, one per line with a
newline after each.
