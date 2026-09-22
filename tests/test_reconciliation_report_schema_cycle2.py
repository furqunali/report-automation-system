from reporting_core.reconciliation_report_schema import validate_reconciliation_report


def test_reconciliation_report_rejects_wrong_ratio():
    payload = {"count": 4, "balanced": 3, "unbalanced": 1, "balanced_ratio": 0.5}
    assert not validate_reconciliation_report(payload)

def test_reconciliation_report_accepts_zero_count():
    payload = {"count": 0, "balanced": 0, "unbalanced": 0, "balanced_ratio": 0}
    assert validate_reconciliation_report(payload)

def test_reconciliation_report_rejects_negative_count():
    payload = {"count": -1, "balanced": 0, "unbalanced": 0, "balanced_ratio": 0}
    assert not validate_reconciliation_report(payload)
