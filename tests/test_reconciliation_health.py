from reporting_core.reconciliation import reconcile_sales
from reporting_core.reconciliation_health import summarize_reconciliation_health

def test_health_ratio():
    result = summarize_reconciliation_health([reconcile_sales(10,10), reconcile_sales(10,11)])
    assert result.count == 2 and result.balanced == 1 and result.unbalanced == 1
    assert result.balanced_ratio == .5

def test_empty_health():
    assert summarize_reconciliation_health([]).balanced_ratio == 0.0
