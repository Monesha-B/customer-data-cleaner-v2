import csv
import os

REQUIRED_FIELDS = ["ID", "name", "email"]


def read_customers(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


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

    # 3. Duplicate ID (Rule A: any ID seen earlier counts)
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


def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    os.makedirs("output", exist_ok=True)

    records = read_customers("data/customers.csv")
    valid, invalid = clean_customers(records)

    write_csv("output/valid_customers.csv", valid, REQUIRED_FIELDS)
    write_csv(
        "output/invalid_customers.csv",
        invalid,
        ["line"] + REQUIRED_FIELDS + ["reason"],
    )

    print(f"Valid: {len(valid)}")
    print(f"Invalid: {len(invalid)}")
    for row in invalid:
        print(f"  line {row['line']}: ID {row.get('ID')} ({row.get('name')}): {row['reason']}")


if __name__ == "__main__":
    main()