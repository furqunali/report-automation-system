import sys
from pathlib import Path

import pytest

from reporting_core.ingestion import (
    HeaderRules,
    MissingDependencyError,
    UnsupportedFormatError,
    normalize_key,
    normalize_status,
    parse_number,
    read_csv,
    read_file,
    read_xlsx,
)
from reporting_core.models import ReportRow
from reporting_core.validation import validate_row

FIXTURES = Path(__file__).parent / "fixtures"


# --------------------------------------------------------------------------- #
#  Header rules engine
# --------------------------------------------------------------------------- #
def test_normalize_key_squeezes_punctuation_and_case():
    assert normalize_key("  Sales ($) ") == "sales"
    assert normalize_key("Qty_Sold") == "qty sold"
    assert normalize_key(None) == ""


def test_rules_resolve_known_and_unknown_headers():
    rules = HeaderRules()
    assert rules.resolve("Store Name") == "site"
    assert rules.resolve("QTY ORDERED") == "quantity"
    assert rules.resolve("Extended Cost") == "sales"
    assert rules.resolve("Widgets Per Fortnight") is None


def test_rules_map_headers_by_index_last_column_wins():
    rules = HeaderRules()
    headers = ["Store", "Amount", "Total"]  # two sales aliases collide
    mapping = rules.map_headers(headers)
    assert mapping == {0: "site", 1: "sales", 2: "sales"}


def test_add_rule_registers_new_alias_and_rejects_bad_field():
    rules = HeaderRules()
    rules.add_rule("Outlet", "site")
    assert rules.resolve("outlet") == "site"
    with pytest.raises(ValueError, match="canonical field"):
        rules.add_rule("whatever", "not_a_field")


# --------------------------------------------------------------------------- #
#  Value parsing
# --------------------------------------------------------------------------- #
def test_parse_number_handles_currency_thousands_and_accounting_negatives():
    assert parse_number("$1,234.50") == 1234.50
    assert parse_number("(123.45)") == -123.45
    assert parse_number("$ (1,234.50)") == -1234.50
    assert parse_number("") == 0.0
    assert parse_number("n/a") == 0.0
    assert parse_number(42) == 42.0
    assert parse_number(True) == 0.0  # bools are not real quantities


def test_normalize_status_explicit_blank_and_inferred():
    assert normalize_status("Active", quantity=5) == "Active"
    assert normalize_status("No Movement", quantity=0) == "No Movement"
    assert normalize_status("INACTIVE", quantity=3) == "No Movement"
    # blank status is inferred from quantity
    assert normalize_status("", quantity=0) == "No Movement"
    assert normalize_status(None, quantity=10) == "Active"


# --------------------------------------------------------------------------- #
#  CSV reader (pure stdlib) against a real messy fixture
# --------------------------------------------------------------------------- #
def test_read_csv_maps_variant_headers_to_canonical_rows():
    rows = read_csv(FIXTURES / "messy_commissary.csv")

    # the fully blank spacer line is dropped
    assert len(rows) == 5
    assert all(isinstance(r, ReportRow) for r in rows)

    first = rows[0]
    assert first == ReportRow(
        site="Demo Store 01",
        category="Beverages",
        product="Cola 20oz",
        quantity=46.0,
        sales=806.38,
        status="Active",
    )
    validate_row(first)  # canonical output is valid by construction


def test_read_csv_thousands_and_blank_status_inference():
    rows = read_csv(FIXTURES / "messy_commissary.csv")
    bread = next(r for r in rows if r.product == "Bread Loaf")
    assert bread.quantity == 1204.0
    assert bread.sales == 3014.50
    # status column was blank but quantity > 0 -> Active
    assert bread.status == "Active"


def test_read_csv_preserves_accounting_negative_from_source():
    rows = read_csv(FIXTURES / "messy_commissary.csv")
    oil = next(r for r in rows if r.product == "Motor Oil 1qt")
    assert oil.sales == -12.50


def test_read_csv_empty_file_returns_empty(tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")
    assert read_csv(empty) == []


# --------------------------------------------------------------------------- #
#  XLSX reader
# --------------------------------------------------------------------------- #
def _write_xlsx(path: Path) -> None:
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Movement"
    ws.append(["Location", "Department", "Item", "Units Sold", "Amount", "State"])
    ws.append(["Demo Store 07", "Frozen", "Ice Cream Tub", 12, 84.00, "Active"])
    ws.append(["Demo Store 07", "Frozen", "Frozen Pizza", 0, 0, "No Movement"])
    wb.save(path)


def test_read_xlsx_reads_all_rows_with_canonical_mapping(tmp_path):
    pytest.importorskip("openpyxl")
    book = tmp_path / "report.xlsx"
    _write_xlsx(book)

    rows = read_xlsx(book)
    assert len(rows) == 2
    assert rows[0] == ReportRow(
        site="Demo Store 07",
        category="Frozen",
        product="Ice Cream Tub",
        quantity=12.0,
        sales=84.0,
        status="Active",
    )
    assert rows[1].status == "No Movement"


def test_read_xlsx_missing_dependency_raises_clear_error(tmp_path, monkeypatch):
    # Simulate openpyxl not being installed: importing it raises ImportError.
    monkeypatch.setitem(sys.modules, "openpyxl", None)
    with pytest.raises(MissingDependencyError, match="pip install openpyxl"):
        read_xlsx(tmp_path / "whatever.xlsx")


# --------------------------------------------------------------------------- #
#  Dispatch
# --------------------------------------------------------------------------- #
def test_read_file_dispatches_on_extension():
    rows = read_file(FIXTURES / "messy_commissary.csv")
    assert len(rows) == 5


def test_read_file_rejects_unknown_extension(tmp_path):
    junk = tmp_path / "report.pdf"
    junk.write_text("nope", encoding="utf-8")
    with pytest.raises(UnsupportedFormatError, match="unsupported report format"):
        read_file(junk)
