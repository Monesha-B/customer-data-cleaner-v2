# Customer Data Cleaner V2

A Python project that cleans customer CSV files, identifies invalid records, handles inconsistent column headers, and optionally stores valid customer records in a SQLite database.

## Features

- **CSV processing:** Reads customer data from CSV files.
- **Header normalization:** Supports alternative column names such as `Customer ID`, `Full Name`, and `E-MAIL`.
- **Data validation:** Checks for missing IDs, names, and emails, as well as invalid email formats.
- **Duplicate detection:** Identifies repeated customer IDs.
- **Error reporting:** Reports invalid records with line numbers and reasons.
- **CSV output:** Separates valid and invalid records into different files.
- **SQLite integration:** Optionally loads valid records into a database.
- **Command-line interface:** Accepts input files and database options.
- **Automated testing:** Uses `pytest` to verify functionality.

## Project Structure

```text
customer-data-cleaner-v2/
├── data/
│   ├── customers.csv
│   └── customers_messy_headers.csv
├── output/
│   ├── valid_customers.csv
│   ├── invalid_customers.csv
│   └── customers.db
├── cleaner.py
├── test_cleaner.py
├── README.md
└── .gitignore
```

The `.venv/` virtual environment and generated cache files are excluded from Git using `.gitignore`. Database files (`*.db`) are also ignored.

## Requirements

- Python 3
- `pytest` for running automated tests
- SQLite for database storage

## Installation

Clone the repository:

```bash
git clone https://github.com/Monesha-B/customer-data-cleaner-v2.git
cd customer-data-cleaner-v2
```

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

Install the testing dependency:

```bash
python -m pip install pytest
```

## Usage

### 1. Clean a CSV file

```bash
python cleaner.py
```

This processes the default customer dataset.

### 2. Process a CSV with alternative headers

```bash
python cleaner.py data/customers_messy_headers.csv
```

The program normalizes supported column names before validating the records.

### 3. Save results to SQLite

```bash
python cleaner.py data/customers_messy_headers.csv --db output/customers.db
```

This command cleans the input file, creates or updates the SQLite database, and loads valid customer records into the `customers` table.

### 4. View the output

The program generates:

- `output/valid_customers.csv` — valid customer records.
- `output/invalid_customers.csv` — records that failed validation.

The terminal reports the number of valid and invalid records and explains why records were rejected.

## Example Output

```text
Valid: 2
Invalid: 1
  line 3: ID 2 (Amit): missing email
Loaded 2 valid record(s) into output/customers.db
```

In this example, two records passed validation, one record was rejected because its email was missing, and the two valid records were loaded into SQLite.

## Query the SQLite Database

Open the database:

```bash
sqlite3 output/customers.db
```

Display the available tables:

```sql
.tables
```

Format the query output:

```sql
.headers on
.mode column
```

View all customer records:

```sql
SELECT * FROM customers;
```

Exit SQLite:

```sql
.exit
```

## Run Automated Tests

Run the test suite:

```bash
pytest -v
```

The tests cover the CSV cleaning and validation functionality. The current test suite has passed **33 tests** in the development environment.

## Technologies Used

- Python
- CSV processing
- SQLite
- SQL (Structured Query Language)
- `argparse` for command-line arguments
- `pytest` for automated testing
- Git and GitHub for version control

## Learning Outcomes

This project demonstrates practical experience with:

- Data cleaning and validation
- Handling inconsistent CSV headers
- Identifying missing, invalid, and duplicate data
- File input/output
- Relational database basics
- Writing and running automated tests
- Command-line tools and Git workflows

## Future Improvements

- Add structured logging.
- Generate data-quality summary reports.
- Support configurable validation rules.
- Add database queries for reporting and analysis.
- Improve test coverage for edge cases.

## Author

Monesha Balasambandam

GitHub: [Monesha-B](https://github.com/Monesha-B)
