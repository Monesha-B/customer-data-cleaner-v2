import argparse
import csv
import os
import sqlite3
import sys

REQUIRED_FIELDS = ["ID", "name", "email"]

# Cleaned header names (left) -> standard names (right)
HEADER_ALIASES = {
    "id": "ID",
    "customerid": "ID",
    "name": "name",
    "fullname": "name",
    "email": "email",
    "emailaddress": "email",
}


class MissingColumnsError(Exception):
    """Raised when the file has no column for a required field."""


# ---------- headers ----------

def normalize_header(header):
    """Lowercase, trim, and remove '-', '_' and spaces."""
    return (
        header.strip()
        .lower()
        .replace("-", "")
        .replace("_", "")
        .replace(" ", "")
    )


def analyze_headers(fieldnames):
    """Look at the file's header row.

    Returns (recognized, ignored, duplicates, missing):
      recognized - {original header: standard name}
      ignored    - headers we don't know
      duplicates - headers that map to a name already taken (first one wins)
      missing    - required standard names with no column at all
    """
    recognized = {}
    ignored = []
    duplicates = []

    for header in fieldnames or []:
        standard = HEADER_ALIASES.get(normalize_header(header))
        if standard is None:
            ignored.append(header)
        elif standard in recognized.values():
            duplicates.append(header)
        else:
            recognized[header] = standard

    missing = [f for f in REQUIRED_FIELDS if f not in recognized.values()]
    return recognized, ignored, duplicates, missing


def map_record(record):
    """Rename a row's keys to the standard names.

    Unknown columns are ignored. If two columns map to the same
    standard name, the first one wins.
    """
    mapped = {}
    for key, value in record.items():
        if key is None:  # DictReader uses None for extra values with no header
            continue
        standard = HEADER_ALIASES.get(normalize_header(key))
        if standard and standard not in mapped:
            mapped[standard] = value
    return mapped


# ---------- reading and validating ----------

def read_customers(path):
    """Return (fieldnames, rows). 'utf-8-sig' strips Excel's hidden BOM."""
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return reader.fieldnames, rows


def validate_record(record, seen_ids):
    """Return a list of reasons this record is invalid. Empty list = valid."""
    reasons = []

    # 1. Missing fields (spaces-only counts as missing)
    for field in REQUIRED_FIELDS:
        value = (record.get(field) or "").strip()
        if value == "":
            reasons.append(f"missing {field}")

    # 2. Email format (only if the email is not empty)
    email = (record.get("email") or "").strip()
    if email:
        parts = email.split("@")
        if len(parts) != 2 or parts[0] == "" or "." not in parts[1]:
            reasons.append("invalid email format")

    # 3. Duplicate ID (any ID seen earlier counts)
    cust_id = (record.get("ID") or "").strip()
    if cust_id and cust_id in seen_ids:
        reasons.append("duplicate ID")

    return reasons


def clean_customers(records):
    """Split records into (valid, invalid). Invalid ones get 'line' and 'reason'."""
    valid = []
    invalid = []
    seen_ids = set()

    # start=2 because line 1 of the file is the header
    for line, record in enumerate(records, start=2):
        reasons = validate_record(record, seen_ids)
        if reasons:
            invalid.append({"line": line, **record, "reason": "; ".join(reasons)})
        else:
            valid.append(record)
        seen_ids.add((record.get("ID") or "").strip())

    return valid, invalid


# ---------- writing ----------

def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def load_into_db(db_path, records):
    """Insert valid records into a SQLite table. Re-running updates, never duplicates."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS customers ("
            "id TEXT PRIMARY KEY, "
            "name TEXT NOT NULL, "
            "email TEXT NOT NULL)"
        )
        for record in records:
            conn.execute(
                "INSERT INTO customers (id, name, email) VALUES (?, ?, ?) "
                "ON CONFLICT(id) DO UPDATE SET "
                "name = excluded.name, email = excluded.email",
                (
                    record["ID"].strip(),
                    record["name"].strip(),
                    record["email"].strip(),
                ),
            )
        conn.commit()
    finally:
        conn.close()
    return len(records)


# ---------- putting it together ----------

def process_file(path, output_dir="output", db_path=None):
    """Read, map, validate, split, write. Returns a summary dict."""
    fieldnames, raw_rows = read_customers(path)
    recognized, ignored, duplicates, missing = analyze_headers(fieldnames)

    if missing:
        raise MissingColumnsError(
            "file is missing required column(s): " + ", ".join(missing)
        )

    records = []
    for raw in raw_rows:
        records.append(map_record(raw))

    valid, invalid = clean_customers(records)

    os.makedirs(output_dir, exist_ok=True)
    write_csv(os.path.join(output_dir, "valid_customers.csv"), valid, REQUIRED_FIELDS)
    write_csv(
        os.path.join(output_dir, "invalid_customers.csv"),
        invalid,
        ["line"] + REQUIRED_FIELDS + ["reason"],
    )

    loaded = None
    if db_path:
        loaded = load_into_db(db_path, valid)

    return {
        "valid": valid,
        "invalid": invalid,
        "ignored": ignored,
        "duplicates": duplicates,
        "loaded": loaded,
    }


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Clean a customer CSV file.")
    parser.add_argument(
        "path",
        nargs="?",
        default="data/customers.csv",
        help="CSV file to clean (default: data/customers.csv)",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="SQLite file to load the valid records into",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    try:
        result = process_file(args.path, db_path=args.db)
    except FileNotFoundError:
        print(f"Error: file not found: {args.path}")
        return 1
    except MissingColumnsError as err:
        print(f"Error: {err}")
        return 1

    if result["ignored"]:
        print("Warning: ignored columns: " + ", ".join(result["ignored"]))
    if result["duplicates"]:
        print(
            "Warning: duplicate columns skipped (first one wins): "
            + ", ".join(result["duplicates"])
        )

    print(f"Valid: {len(result['valid'])}")
    print(f"Invalid: {len(result['invalid'])}")
    for row in result["invalid"]:
        print(
            f"  line {row['line']}: ID {row.get('ID')} "
            f"({row.get('name')}): {row['reason']}"
        )

    if result["loaded"] is not None:
        print(f"Loaded {result['loaded']} valid record(s) into {args.db}")

    return 0


if __name__ == "__main__":
    sys.exit(main())