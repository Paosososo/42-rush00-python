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

On the first run, enter opening balance and reserve. Opening balance is set
once, including when it is zero. Later runs automatically open the existing
`moneypilot.json` beside `main.py` without asking for another opening balance.
Changes to records and reserve are saved automatically.

## Main menu

| Choice | Action |
| --- | --- |
| 1 | Add, view, update, or remove actual transactions |
| 2 | Show actual balance, category spending, and reserve runway |
| 3 | Check a proposed one-time purchase |
| 4 | Add, view, update, or remove recurring monthly plans |
| 5 | Filter actual history by type, category, and date range |
| 6 | Show six projected monthly closing balances |
| 7 | Change reserve without changing opening balance |
| 8 | Export a separate JSON backup |
| 9 | Import JSON and overwrite the current saved dataset |
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
| [storage.py](storage.py) | Open or create saved data, upgrade old files, and write JSON through a temporary file |
| [auteur](auteur) | The team's Intra login entries |
| `moneypilot.json` | The automatic saved session beside `main.py` |

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
Opening balance cannot be edited through the menu after setup. Option 7 changes
only the reserve. Actual expenses may produce a negative balance because the ledger records what
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

At setup, reserve must be between zero and opening balance. When changing it
later, the limit is the current balance, including recorded income and expenses.
An invalid reserve is rejected without changing the old value or opening cash.
This rule checks reserve settings. Actual payments remain recordable if later
spending puts balance below reserve; the existing runway calculation reports
zero in that situation.

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

## First-time setup, saving, and JSON imports

The default data file is `moneypilot.json` beside `main.py`. Its path is based
on the script, so launching from another directory uses the same saved session.

If there is no file, the app creates an unfinished session and asks for opening
balance and reserve. Both must pass validation before setup is completed and
saved. An interrupted setup is retried on the next run. A completed setup is
not repeated, even if the account started at zero or later reaches zero.

The new format is version 2 and stores a `setup_complete` flag. Existing
version 1 files are recognized as already initialized, including zero-balance
files. Their opening amount, history, plans, and counters are preserved. The
upgrade occurs in memory; a later save writes the version 2 format.

Actual-record changes, plan changes, and reserve changes automatically save
the complete session. If saving fails, the app says the change is still only
in memory. It retries at exit and asks before discarding remaining unsaved
changes. EOF and Ctrl+C also retry pending changes.

Option **8** exports a backup, defaulting to `moneypilot_backup.json`. It asks
before overwriting an existing destination. Custom parent directories must
already exist.

Option **9** imports a JSON backup. After validation, type `LOAD` to overwrite
the current saved dataset. The imported opening balance, records, plans, and
settings replace the previous dataset; they are not added to it. The replacement
is saved before switching the live session and is reopened on the next run.
An unfinished setup cannot be imported over an initialized account.

A failed import keeps the current session. A damaged startup file is reported
and kept unchanged rather than reset. Storage writes a complete temporary file
before replacing an existing save.

## Validation and business rules

- Payment amounts, monthly totals, and purchase prices must be positive.
  Opening balance and reserve may be zero. Input allows at most two decimal
  places and up to 1,000,000,000.00 baht per entered amount.
- Opening balance is initialized once. A reserve setting cannot exceed the
  current balance at the time it is set or changed.
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

These are fictional practice values. Use a separate project copy without a
saved data file to practise a first run while keeping your existing data.

1. At first-time setup, enter opening balance `10000` and reserve `2000`.
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
10. Exit and restart to show that the saved account reopens automatically.
    Export a backup with option 8. Import it through option 9 and type `LOAD`
    to demonstrate replacement without duplicating the opening balance.

## Checking the program

To check Python syntax from the folder containing `main.py`:

```sh
python3 -m py_compile main.py transactions.py finance.py storage.py
```

This checks Python syntax. Use the walkthrough above to check the program's
behavior manually.

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
