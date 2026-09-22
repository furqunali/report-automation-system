from reporting_core.reconciliation_health import ReconciliationHealth
from reporting_core.reconciliation_report import reconciliation_report_dict, reconciliation_report_json

def test_reconciliation_export_is_deterministic():
    result = ReconciliationHealth(10, 8, 2, 0.8)
    assert reconciliation_report_dict(result) == {
        "count": 10, "balanced": 8, "unbalanced": 2, "balanced_ratio": 0.8
    }
    assert reconciliation_report_json(result) == '{"balanced": 8, "balanced_ratio": 0.8, "count": 10, "unbalanced": 2}'


def test_reconciliation_export_rejects_wrong_type():
    try:
        reconciliation_report_dict("bad")
    except TypeError:
        pass
    else:
        raise AssertionError("expected TypeError")


def test_export_enforces_schema():
    assert reconciliation_report_dict(ReconciliationHealth(1, 1, 0, 1.0))["count"] == 1
