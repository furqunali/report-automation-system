from reporting_core.report_contract import validate_reconciliation_payload

def test_accepts_complete_payload():
    assert validate_reconciliation_payload({"expected_sales":100,"observed_sales":100,"delta":0,"balanced":True})

def test_rejects_missing_fields():
    try:
        validate_reconciliation_payload({"expected_sales":100})
    except ValueError:
        return
    raise AssertionError("expected ValueError")
