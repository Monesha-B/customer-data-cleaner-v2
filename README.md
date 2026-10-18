# Customer Data Cleaner

A Python tool that reads a messy customer CSV, checks every record against validation rules, and splits the data into a valid file and an invalid file. Every rejected record gets a plain-English reason and its line number in the original file.

## The problem

Companies receive customer files from many sources, and the data is rarely clean. Missing emails, malformed emails, and repeated IDs can break an import or corrupt a database. Someone has to find the bad rows before the data is loaded.

## How it works

```
CSV file -> Read -> Check each record -> Separate -> Report
```

1. **Read** the CSV into a list of records.
2. **Check** each record against the rules below.
3. **Separate** records into valid and invalid.
4. **Report** every rejection with its line number and all of its reasons.

## Validation rules

| Rule | Reason shown |
|---|---|
| ID, name, or email is empty (spaces only counts as empty) | `missing ID`, `missing name`, `missing email` |
| Email does not have exactly one `@`, text before it, and a `.` after it | `invalid email format` |
| ID already appeared on an earlier line | `duplicate ID` |

A record can have several reasons, joined with `;`.

## Design decisions

- **All reasons are reported, not just the first.** A reviewer can fix everything in one pass instead of re-running the tool repeatedly.
- **Any repeated ID is a duplicate, even if the first row was rejected.** An ID should be unique, so seeing it twice is a data problem someone needs to know about.
- **Spaces-only counts as missing.** Values are trimmed before checking, so `"   "` is treated as empty.
- **Line numbers in the invalid report.** Without them, identical-looking rows cannot be told apart.
- **Plain Python and the built-in `csv` module.** No extra libraries are needed for the core logic.
- **Validation lives in one function that returns a list of reasons.** An empty list means valid. This keeps the logic testable.

## Failure cases tested

Run against `data/customers.csv`:

| Line | Data | Result | Reason |
|---|---|---|---|
| 2 | 1, Shreya | Valid | |
| 3 | 2, Amit, (empty) | Invalid | missing email |
| 4 | 3, Neha | Valid | |
| 5 | 2, Amit, (empty) | Invalid | missing email; duplicate ID |
| 6 | 4, Ravi, `ravi@@example` | Invalid | invalid email format |
| 7 | 5, Priya, (spaces) | Invalid | missing email |
| 8 | 1, Shreya (repeat) | Invalid | duplicate ID |

Edge cases covered by tests: spaces-only email, double `@`, domain with no dot, a record with no `email` key at all, and a repeated ID whose first row was rejected.

## Results

```
Valid: 2
Invalid: 5
  line 3: ID 2 (Amit): missing email
  line 5: ID 2 (Amit): missing email; duplicate ID
  line 6: ID 4 (Ravi): invalid email format
  line 7: ID 5 (Priya): missing email
  line 8: ID 1 (Shreya): duplicate ID
```

10 automated tests, all passing.

Output files:

- `output/valid_customers.csv`: clean records
- `output/invalid_customers.csv`: rejected records with `line` and `reason` columns

## How to run

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pytest
python cleaner.py
pytest -v
```

## Project structure

```
customer-data-cleaner-v2/
├── cleaner.py          # read, validate, split, write
├── test_cleaner.py     # pytest tests
├── data/
│   └── customers.csv   # sample messy input
├── output/             # generated results
└── README.md
```

## Limitations and next steps

- Column headers must match exactly (`ID`, `name`, `email`). Mapping variants like `e-mail` or `E_MAIL` to one standard name is not built yet.
- The email check is a basic structural check, not full email validation.
- Only CSV input is supported.
- Results are written to files. Loading into a database is not part of this project yet.
