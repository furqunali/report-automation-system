import csv
import io

import pytest

from reporting_core.csv_export import (
    CSV_COLUMNS,
    render_rows_csv,
    write_rows_csv,
)
from reporting_core.models import ReportRow


def row(site, product, quantity, sales, status="Active", category="General"):
    return ReportRow(
        site=site,
        category=category,
        product=product,
        quantity=quantity,
        sales=sales,
        status=status,
    )


BASIC = [
    row("Store A", "Cola", 10, 100.00),
    row("Store B", "Chips", 5, 40.50, status="No Movement"),
]


def _parse(document):
    """Round-trip the document through the stdlib csv reader as a consumer would."""
    return list(csv.reader(io.StringIO(document)))


# --- Column contract -------------------------------------------------------


def test_header_is_the_stable_contract():
    md = render_rows_csv([])
    assert md == ",".join(CSV_COLUMNS) + "\r\n"
    assert CSV_COLUMNS == ("site", "category", "product", "quantity", "sales", "status")


def test_every_row_has_exactly_the_contract_columns():
    parsed = _parse(render_rows_csv(BASIC))
    assert parsed[0] == list(CSV_COLUMNS)
    for record in parsed[1:]:
        assert len(record) == len(CSV_COLUMNS)


def test_columns_are_in_declared_order():
    parsed = _parse(render_rows_csv([row("S", "P", 3, 12.0, category="Bev")]))
    assert parsed[1] == ["S", "Bev", "P", "3.00", "12.00", "Active"]


# --- Header toggle ---------------------------------------------------------


def test_include_header_false_omits_header():
    parsed = _parse(render_rows_csv(BASIC, include_header=False))
    assert parsed[0] == ["Store A", "General", "Cola", "10.00", "100.00", "Active"]
    assert len(parsed) == 2


def test_empty_without_header_is_empty_string():
    assert render_rows_csv([], include_header=False) == ""


def test_empty_with_header_is_header_only():
    doc = render_rows_csv([])
    assert doc.count("\r\n") == 1


# --- RFC-4180 escaping -----------------------------------------------------


def test_comma_forces_quoting():
    doc = render_rows_csv([row("A, Inc", "Cola", 1, 10.0)], include_header=False)
    assert doc.startswith('"A, Inc",')
    # And a consumer recovers the original field intact.
    assert _parse(doc)[0][0] == "A, Inc"


def test_double_quote_is_doubled_and_wrapped():
    doc = render_rows_csv([row('The "Big" Mart', "Cola", 1, 10.0)], include_header=False)
    assert doc.startswith('"The ""Big"" Mart",')
    assert _parse(doc)[0][0] == 'The "Big" Mart'


def test_embedded_newline_is_preserved_inside_quotes():
    doc = render_rows_csv([row("Line1\nLine2", "Cola", 1, 10.0)], include_header=False)
    # The field is quoted and the newline is kept, not flattened.
    assert '"Line1\nLine2"' in doc
    record = _parse(doc)[0]
    assert record[0] == "Line1\nLine2"
    # Exactly one logical record despite the embedded newline.
    assert len(_parse(doc)) == 1


def test_crlf_inside_field_is_preserved():
    doc = render_rows_csv([row("A\r\nB", "Cola", 1, 10.0)], include_header=False)
    assert _parse(doc)[0][0] == "A\r\nB"
    assert len(_parse(doc)) == 1


def test_plain_field_is_not_quoted():
    doc = render_rows_csv([row("PlainName", "Cola", 1, 10.0)], include_header=False)
    assert doc.startswith("PlainName,")
    assert '"' not in doc


def test_leading_trailing_spaces_preserved():
    doc = render_rows_csv([row("  spaced  ", "Cola", 1, 10.0)], include_header=False)
    assert _parse(doc)[0][0] == "  spaced  "


# --- Numeric formatting ----------------------------------------------------


def test_numbers_are_fixed_two_decimals_without_separators():
    doc = render_rows_csv([row("S", "P", 1000, 1234567.5)], include_header=False)
    record = _parse(doc)[0]
    assert record[3] == "1000.00"
    assert record[4] == "1234567.50"
    # No thousands separators (which would need quoting / break parsing).
    assert '"' not in doc


def test_negative_zero_is_normalized():
    doc = render_rows_csv([row("S", "P", 0.0, 0.0)], include_header=False)
    record = _parse(doc)[0]
    assert record[3] == "0.00"
    assert record[4] == "0.00"
    assert "-0.00" not in doc


def test_rounding_is_deterministic():
    doc = render_rows_csv([row("S", "P", 1.005, 2.675)], include_header=False)
    a = render_rows_csv([row("S", "P", 1.005, 2.675)], include_header=False)
    assert doc == a


# --- Line terminators ------------------------------------------------------


def test_records_use_crlf_and_trailing_terminator():
    doc = render_rows_csv(BASIC)
    # 1 header + 2 data rows -> 3 CRLFs (each record terminated).
    assert doc.count("\r\n") == 3
    assert doc.endswith("\r\n")
    # No bare LF outside a CRLF pair (no embedded newlines in this data).
    assert doc.replace("\r\n", "") .count("\n") == 0


def test_output_is_deterministic():
    assert render_rows_csv(BASIC) == render_rows_csv(BASIC)


# --- Validation ------------------------------------------------------------


def test_rejects_non_reportrow_element():
    with pytest.raises(TypeError):
        render_rows_csv([{"site": "A"}])


def test_invalid_row_raises_value_error():
    bad = ReportRow("", "General", "Cola", 1.0, 10.0, "Active")
    with pytest.raises(ValueError):
        render_rows_csv([bad])


def test_negative_sales_row_is_rejected():
    bad = ReportRow("A", "General", "Cola", 1.0, -5.0, "Active")
    with pytest.raises(ValueError):
        render_rows_csv([bad])


# --- File writer -----------------------------------------------------------


def test_write_rows_csv_round_trips(tmp_path):
    target = tmp_path / "nested" / "export.csv"
    returned = write_rows_csv(BASIC, path=str(target))
    assert returned == str(target)
    # Read back in binary to confirm CRLF survived (no newline translation).
    raw = target.read_bytes()
    assert b"\r\n" in raw
    assert raw.decode("utf-8") == render_rows_csv(BASIC)


def test_write_rows_csv_bom(tmp_path):
    target = tmp_path / "export_bom.csv"
    write_rows_csv([row("S", "P", 1, 10.0)], path=str(target), bom=True)
    raw = target.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")


def test_write_rows_csv_no_bom_by_default(tmp_path):
    target = tmp_path / "export_nobom.csv"
    write_rows_csv([row("S", "P", 1, 10.0)], path=str(target))
    raw = target.read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf")


def test_written_file_is_parseable_with_quoted_fields(tmp_path):
    tricky = [
        row('A, "B"', "line\nbreak", 2, 3.5),
        row("Normal", "Cola", 1, 10.0),
    ]
    target = tmp_path / "tricky.csv"
    write_rows_csv(tricky, path=str(target))
    with open(target, newline="", encoding="utf-8") as fh:
        records = list(csv.reader(fh))
    assert records[0] == list(CSV_COLUMNS)
    assert records[1][0] == 'A, "B"'
    assert records[1][2] == "line\nbreak"
    assert records[2] == ["Normal", "General", "Cola", "1.00", "10.00", "Active"]
