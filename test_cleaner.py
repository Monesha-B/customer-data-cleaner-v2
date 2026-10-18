import csv
import sqlite3

import pytest

from cleaner import (
    MissingColumnsError,
    analyze_headers,
    clean_customers,
    load_into_db,
    main,
    map_record,
    normalize_header,
    process_file,
    read_customers,
    validate_record,
    write_csv,
)


def row(id_="1", name="Amit", email="amit@example.com"):
    return {"ID": id_, "name": name, "email": email}


def write_text(folder, name, text):
    path = folder / name
    path.write_text(text, encoding="utf-8", newline="")
    return path


def read_back(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


MESSY_HEADERS = (
    "Customer ID,Full Name,E-MAIL\n"
    "1,Shreya,shreya@example.com\n"
    "2,Amit,\n"
    "3,Neha,neha@example.com\n"
)


# ---------- validate_record ----------

def test_valid_record_has_no_reasons():
    assert validate_record(row(), set()) == []


def test_empty_email_is_missing():
    assert validate_record(row(email=""), set()) == ["missing email"]


def test_spaces_only_email_is_missing():
    assert validate_record(row(email="   "), set()) == ["missing email"]


def test_double_at_is_invalid_format():
    assert validate_record(row(email="ravi@@example"), set()) == ["invalid email format"]


def test_no_dot_in_domain_is_invalid_format():
    assert validate_record(row(email="a@b"), set()) == ["invalid email format"]


def test_duplicate_id():
    assert validate_record(row(), {"1"}) == ["duplicate ID"]


def test_missing_email_key_does_not_crash():
    assert validate_record({"ID": "5", "name": "Ravi"}, set()) == ["missing email"]


# ---------- clean_customers ----------

def test_repeated_id_is_duplicate_even_if_first_was_rejected():
    records = [row("2", "Amit", ""), row("2", "Amit", "")]
    valid, invalid = clean_customers(records)
    assert valid == []
    assert [r["reason"] for r in invalid] == [
        "missing email",
        "missing email; duplicate ID",
    ]


def test_full_sample_file():
    records = [
        row("1", "Shreya", "shreya@example.com"),
        row("2", "Amit", ""),
        row("3", "Neha", "neha@example.com"),
        row("2", "Amit", ""),
        row("4", "Ravi", "ravi@@example"),
        row("5", "Priya", "   "),
        row("1", "Shreya", "shreya@example.com"),
    ]
    valid, invalid = clean_customers(records)
    assert len(valid) == 2
    assert len(invalid) == 5
    assert invalid[1]["reason"] == "missing email; duplicate ID"
    assert invalid[-1]["reason"] == "duplicate ID"


def test_invalid_rows_carry_file_line_numbers():
    records = [row("1"), row("2", "Amit", ""), row("3")]
    valid, invalid = clean_customers(records)
    assert [r["line"] for r in invalid] == [3]


# ---------- field mapping ----------

def test_normalize_header_variants():
    assert normalize_header(" E-Mail ") == "email"
    assert normalize_header("E_MAIL") == "email"
    assert normalize_header("Customer ID") == "customerid"


def test_map_record_renames_columns():
    raw = {"Customer ID": "1", "Full Name": "Shreya", "E-MAIL": "s@x.com"}
    assert map_record(raw) == {"ID": "1", "name": "Shreya", "email": "s@x.com"}


def test_map_record_ignores_unknown_columns():
    raw = {"ID": "1", "name": "A", "email": "a@b.com", "phone": "123"}
    assert "phone" not in map_record(raw)


def test_map_record_first_column_wins_on_conflict():
    raw = {"email": "first@x.com", "Email Address": "second@x.com"}
    assert map_record(raw)["email"] == "first@x.com"


# ---------- analyze_headers ----------

def test_analyze_headers_reports_ignored_duplicates_and_missing():
    recognized, ignored, duplicates, missing = analyze_headers(
        ["ID", "Name", "email", "Email Address", "phone"]
    )
    assert recognized == {"ID": "ID", "Name": "name", "email": "email"}
    assert ignored == ["phone"]
    assert duplicates == ["Email Address"]
    assert missing == []


def test_analyze_headers_finds_missing_required_columns():
    _, _, _, missing = analyze_headers(["ID", "name"])
    assert missing == ["email"]


def test_analyze_headers_handles_no_header_at_all():
    _, _, _, missing = analyze_headers(None)
    assert missing == ["ID", "name", "email"]


# ---------- reading and writing files ----------

def test_read_customers_returns_fieldnames_and_rows(tmp_path):
    path = write_text(tmp_path, "c.csv", MESSY_HEADERS)
    fieldnames, rows = read_customers(path)
    assert fieldnames == ["Customer ID", "Full Name", "E-MAIL"]
    assert len(rows) == 3
    assert rows[0]["Full Name"] == "Shreya"


def test_read_customers_strips_excel_bom(tmp_path):
    path = tmp_path / "bom.csv"
    path.write_bytes(b"\xef\xbb\xbfID,name,email\n1,A,a@b.com\n")
    fieldnames, rows = read_customers(path)
    assert fieldnames[0] == "ID"
    assert rows[0]["ID"] == "1"


def test_write_csv_round_trip(tmp_path):
    path = tmp_path / "out.csv"
    write_csv(path, [row("1", "A", "a@b.com")], ["ID", "name", "email"])
    assert read_back(path) == [{"ID": "1", "name": "A", "email": "a@b.com"}]


# ---------- process_file ----------

def test_process_file_with_messy_headers(tmp_path):
    path = write_text(tmp_path, "messy.csv", MESSY_HEADERS)
    out = tmp_path / "out"
    result = process_file(path, output_dir=str(out))
    assert len(result["valid"]) == 2
    assert len(result["invalid"]) == 1
    assert read_back(out / "valid_customers.csv")[0]["name"] == "Shreya"
    invalid_rows = read_back(out / "invalid_customers.csv")
    assert invalid_rows[0]["line"] == "3"
    assert invalid_rows[0]["reason"] == "missing email"


def test_process_file_reports_ignored_columns(tmp_path):
    path = write_text(tmp_path, "p.csv", "ID,name,email,phone\n1,A,a@b.com,555\n")
    result = process_file(path, output_dir=str(tmp_path / "out"))
    assert result["ignored"] == ["phone"]


def test_process_file_raises_when_column_missing(tmp_path):
    path = write_text(tmp_path, "nomail.csv", "ID,name\n1,A\n")
    with pytest.raises(MissingColumnsError) as err:
        process_file(path, output_dir=str(tmp_path / "out"))
    assert "email" in str(err.value)


def test_process_file_does_not_write_outputs_when_column_missing(tmp_path):
    path = write_text(tmp_path, "nomail.csv", "ID,name\n1,A\n")
    out = tmp_path / "out"
    with pytest.raises(MissingColumnsError):
        process_file(path, output_dir=str(out))
    assert not out.exists()


# ---------- database ----------

def fetch_all(db_path):
    conn = sqlite3.connect(db_path)
    try:
        return conn.execute("SELECT id, name, email FROM customers ORDER BY id").fetchall()
    finally:
        conn.close()


def test_load_into_db_inserts_valid_records(tmp_path):
    db = tmp_path / "c.db"
    count = load_into_db(db, [row("1", "A", "a@b.com"), row("2", "B", "b@b.com")])
    assert count == 2
    assert fetch_all(db) == [("1", "A", "a@b.com"), ("2", "B", "b@b.com")]


def test_load_into_db_twice_does_not_duplicate(tmp_path):
    db = tmp_path / "c.db"
    load_into_db(db, [row("1", "A", "a@b.com")])
    load_into_db(db, [row("1", "A", "a@b.com")])
    assert len(fetch_all(db)) == 1


def test_load_into_db_updates_changed_record(tmp_path):
    db = tmp_path / "c.db"
    load_into_db(db, [row("1", "A", "old@b.com")])
    load_into_db(db, [row("1", "A", "new@b.com")])
    assert fetch_all(db) == [("1", "A", "new@b.com")]


def test_process_file_loads_only_valid_records_into_db(tmp_path):
    path = write_text(tmp_path, "messy.csv", MESSY_HEADERS)
    db = tmp_path / "c.db"
    result = process_file(path, output_dir=str(tmp_path / "out"), db_path=str(db))
    assert result["loaded"] == 2
    assert [r[0] for r in fetch_all(db)] == ["1", "3"]


# ---------- main (command line) ----------

def test_main_success_prints_summary(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    path = write_text(tmp_path, "messy.csv", MESSY_HEADERS)
    assert main([str(path)]) == 0
    printed = capsys.readouterr().out
    assert "Valid: 2" in printed
    assert "Invalid: 1" in printed
    assert "line 3: ID 2 (Amit): missing email" in printed


def test_main_warns_about_ignored_columns(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    path = write_text(tmp_path, "p.csv", "ID,name,email,phone\n1,A,a@b.com,555\n")
    assert main([str(path)]) == 0
    assert "Warning: ignored columns: phone" in capsys.readouterr().out


def test_main_returns_1_when_column_missing(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    path = write_text(tmp_path, "nomail.csv", "ID,name\n1,A\n")
    assert main([str(path)]) == 1
    assert "missing required column(s): email" in capsys.readouterr().out


def test_main_returns_1_when_file_not_found(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    assert main(["nope.csv"]) == 1
    assert "file not found" in capsys.readouterr().out


def test_main_db_flag_loads_database(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    path = write_text(tmp_path, "messy.csv", MESSY_HEADERS)
    db = tmp_path / "c.db"
    assert main([str(path), "--db", str(db)]) == 0
    assert "Loaded 2 valid record(s)" in capsys.readouterr().out
    assert len(fetch_all(db)) == 2