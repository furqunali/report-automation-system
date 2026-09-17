import pytest

from reporting_core.models import ReportRow, ReportSummary
from reporting_core.validation import validate_row, validate_summary


def test_valid_row_passes() -> None:
    validate_row(ReportRow("Store 01", "Beverages", "Water", 10, 25.0, "Active"))


def test_negative_quantity_is_rejected() -> None:
    with pytest.raises(ValueError, match="quantity"):
        validate_row(ReportRow("Store 01", "Beverages", "Water", -1, 25.0, "Active"))


def test_invalid_status_is_rejected() -> None:
    with pytest.raises(ValueError, match="status"):
        validate_row(ReportRow("Store 01", "Beverages", "Water", 1, 25.0, "Unknown"))


def test_summary_counts_are_exposed() -> None:
    summary = ReportSummary(100.0, 20.0, 8, 2)
    assert summary.product_count == 10


def test_negative_summary_is_rejected() -> None:
    with pytest.raises(ValueError, match="total_sales"):
        validate_summary(ReportSummary(-1.0, 20.0, 8, 2))
