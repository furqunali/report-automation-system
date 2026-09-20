from reporting_core.anomalies import find_anomalies
from reporting_core.models import ReportRow


def row(quantity=2, sales=10, status="Active"):
    return ReportRow("Site A", "Category", "Product", quantity, sales, status)


def test_detects_negative_values():
    anomalies = find_anomalies([row(quantity=-1), row(sales=-5)])
    assert [item.code for item in anomalies] == ["negative_quantity", "negative_sales"]


def test_valid_rows_have_no_anomalies():
    assert find_anomalies([row(), row(quantity=0, sales=0, status="No Movement")]) == []


def test_detects_invalid_status():
    item = row()
    object.__setattr__(item, "status", "Unknown")
    assert find_anomalies([item])[0].code == "invalid_status"
