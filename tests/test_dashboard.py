import json
from pathlib import Path

import pytest

from reporting_core.dashboard import (
    RECORD_FIELDS,
    build_dashboard_payload,
    build_summary,
    coerce_number,
    generate_data_js,
    is_no_movement,
    normalize_record,
    render_data_js,
)

DASHBOARD_HTML = Path(__file__).resolve().parents[1] / "dashboard" / "dashboard.html"


def rec(site="Store 1", category="Beverages", product="Cola",
        quantity=2, sales="10.00", status="Active", **extra):
    row = {
        "Site": site, "Category": category, "Product": product,
        "Quantity": quantity, "Sales": sales, "Status": status,
    }
    row.update(extra)
    return row


# --------------------------------------------------------------------------- #
#  Numeric coercion
# --------------------------------------------------------------------------- #
def test_coerce_number_handles_currency_commas_and_accounting_negatives():
    assert coerce_number("$1,234.50") == 1234.50
    assert coerce_number("(1,234.50)") == -1234.50
    assert coerce_number("$ (99.99)") == -99.99
    assert coerce_number("") == 0.0
    assert coerce_number("n/a") == 0.0
    assert coerce_number(42) == 42.0


def test_coerce_number_ignores_non_finite_numbers():
    assert coerce_number("NaN") == 0.0
    assert coerce_number("inf") == 0.0
    assert coerce_number("-Infinity") == 0.0


def test_is_no_movement_is_case_insensitive():
    assert is_no_movement("No Movement")
    assert is_no_movement("  INACTIVE ")
    assert not is_no_movement("Active")
    assert not is_no_movement("")


# --------------------------------------------------------------------------- #
#  Summary KPIs
# --------------------------------------------------------------------------- #
def test_build_summary_totals_and_movement_split():
    rows = [
        rec(sales="10", quantity=1, status="Active"),
        rec(sales="$2,000.50", quantity="3", status="Active"),
        rec(sales="0", quantity=0, status="No Movement"),
    ]
    summary = build_summary(rows, "2026-09-21 14:30:45", master_file="master.csv")
    assert summary.total_records == 3
    assert summary.total_sales == 2010.50
    assert summary.total_quantity == 4
    assert summary.active_products == 2
    assert summary.no_movement == 1
    assert summary.processing_date == "2026-09-21 14:30:45"
    assert summary.master_file == "master.csv"


def test_build_summary_empty_is_safe():
    summary = build_summary([], "2026-09-21 00:00:00")
    assert summary.total_records == 0
    assert summary.total_sales == 0.0
    assert summary.total_quantity == 0.0
    assert summary.active_products == 0
    assert summary.no_movement == 0
    assert summary.master_file == ""


# --------------------------------------------------------------------------- #
#  Record normalization
# --------------------------------------------------------------------------- #
def test_normalize_record_orders_expected_fields_first_and_keeps_extras():
    row = {"Report_Name": "r1", "Sales": "5", "Site": "S", "Category": "C",
           "Product": "P", "Quantity": "1", "Status": "Active"}
    out = normalize_record(row)
    assert list(out)[: len(RECORD_FIELDS)] == list(RECORD_FIELDS)
    assert out["Report_Name"] == "r1"  # extra preserved after the core fields


def test_normalize_record_defaults_missing_fields_to_empty_string():
    out = normalize_record({"Product": "P"})
    for field in RECORD_FIELDS:
        assert field in out
    assert out["Site"] == ""
    assert out["Product"] == "P"


# --------------------------------------------------------------------------- #
#  Payload shape — this is exactly what dashboard.html consumes
# --------------------------------------------------------------------------- #
def test_payload_has_summary_and_records_top_level_keys():
    payload = build_dashboard_payload([rec()], "2026-09-21 14:30:45", "m.csv")
    assert set(payload) == {"summary", "records"}
    assert payload["summary"]["total_records"] == 1
    assert len(payload["records"]) == 1
    for field in RECORD_FIELDS:
        assert field in payload["records"][0]


def test_render_data_js_is_valid_and_reparses_to_the_payload():
    payload = build_dashboard_payload(
        [rec(sales="10"), rec(product="Water", sales="5", status="No Movement")],
        "2026-09-21 14:30:45", "m.csv",
    )
    js = render_data_js(payload)
    assert js.startswith("window.REPORT_DATA = ")
    assert js.rstrip().endswith(";")

    # Strip the JS wrapper and the payload must round-trip through JSON intact.
    body = js.strip()[len("window.REPORT_DATA = "):].rstrip().rstrip(";")
    assert json.loads(body) == payload


def test_render_data_js_is_deterministic_regardless_of_source_key_order():
    a = build_dashboard_payload([rec()], "2026-09-21 14:30:45", "m.csv")
    # Same data, deliberately different insertion order in the record dict.
    reordered = {"Status": "Active", "Sales": "10.00", "Quantity": 2,
                 "Product": "Cola", "Category": "Beverages", "Site": "Store 1"}
    b = build_dashboard_payload([reordered], "2026-09-21 14:30:45", "m.csv")
    assert render_data_js(a) == render_data_js(b)


# --------------------------------------------------------------------------- #
#  File writing
# --------------------------------------------------------------------------- #
def test_generate_data_js_writes_loadable_file(tmp_path):
    target = tmp_path / "dashboard" / "data.js"
    out = generate_data_js([rec()], target, "2026-09-21 14:30:45", "m.csv")
    assert out == target
    text = target.read_text(encoding="utf-8")
    assert text.startswith("window.REPORT_DATA = ")
    body = text.strip()[len("window.REPORT_DATA = "):].rstrip().rstrip(";")
    loaded = json.loads(body)
    assert loaded["summary"]["total_records"] == 1


# --------------------------------------------------------------------------- #
#  Contract lock: the emitted fields are the ones dashboard.html actually reads
# --------------------------------------------------------------------------- #
def test_emitted_fields_match_what_dashboard_html_reads():
    html = DASHBOARD_HTML.read_text(encoding="utf-8")
    # Global + top-level keys the page depends on.
    assert "window.REPORT_DATA" in html
    assert ".records" in html
    assert "summary.processing_date" in html
    # Every record field we emit must be referenced by the dashboard script.
    for field in RECORD_FIELDS:
        assert field in html, f"dashboard.html does not reference record field {field!r}"


def test_coerce_number_matches_ingestion_for_booleans():
    assert coerce_number(True) == 0.0
    assert coerce_number(False) == 0.0


def test_normalize_record_rejects_non_mapping():
    import pytest
    with pytest.raises(TypeError, match="record must be a mapping"):
        normalize_record(None)  # type: ignore[arg-type]
