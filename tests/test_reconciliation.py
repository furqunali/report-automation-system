from reporting_core.reconciliation import reconcile_sales

def test_reconciliation_rejects_non_numeric_values():
    try:
        reconcile_sales("100", 100)
    except TypeError:
        return
    raise AssertionError("expected TypeError")

def test_reconciliation_accepts_values_within_tolerance():
    result = reconcile_sales(100, 100.005, tolerance=0.01)
    assert result.balanced is True
