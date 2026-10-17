from cleaner import clean_customers, validate_record


def row(id_="1", name="Amit", email="amit@example.com"):
    return {"ID": id_, "name": name, "email": email}


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