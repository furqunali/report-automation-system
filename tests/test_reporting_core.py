import pytest

from reporting_core.models import ReportRow, ReportSummary
from reporting_core.validation import validate_row, validate_summary


def test_valid_row_passes():
    validate_row(ReportRow("Store 1", "Food", "Item A", 4, 120.5, "Active"))


def test_row_rejects_negative_sales():
    row = ReportRow("Store 1", "Food", "Item A", 4, -1, "Active")
    with pytest.raises(ValueError, match="sales"):
        validate_row(row)


def test_row_rejects_blank_product():
    row = ReportRow("Store 1", "Food", "", 4, 10, "Active")
    with pytest.raises(ValueError, match="product"):
        validate_row(row)


def test_summary_product_count_is_derived():
    summary = ReportSummary(100, 25, 6, 2)
    validate_summary(summary)
    assert summary.product_count == 8


def test_summary_rejects_negative_counts():
    summary = ReportSummary(100, 25, -1, 2)
    with pytest.raises(ValueError, match="counts"):
        validate_summary(summary)
