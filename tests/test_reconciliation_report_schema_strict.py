from reporting_core.reconciliation_report_schema import validate_reconciliation_report


def _valid_report() -> dict:
    return {"count": 4, "balanced": 3, "unbalanced": 1, "balanced_ratio": 0.75}


def test_schema_rejects_bool_as_count():
    payload = _valid_report()
    payload["count"] = True
    assert not validate_reconciliation_report(payload)


def test_schema_rejects_bool_as_ratio():
    payload = _valid_report()
    payload["balanced_ratio"] = True
    assert not validate_reconciliation_report(payload)
