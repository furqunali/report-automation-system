from reporting_core.reconciliation_report_schema import validate_reconciliation_report

def test_valid_reconciliation_schema():
    assert validate_reconciliation_report({"count":10,"balanced":8,"unbalanced":2,"balanced_ratio":0.8})

def test_counts_must_reconcile():
    assert not validate_reconciliation_report({"count":10,"balanced":7,"unbalanced":2,"balanced_ratio":0.7})
