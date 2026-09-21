from reporting_core.reconciliation import reconcile_sales
from reporting_core.reconciliation_direction import summarize_reconciliation_direction

def test_counts_delta_directions():
    result=summarize_reconciliation_direction([reconcile_sales(10,11),reconcile_sales(10,9),reconcile_sales(10,10)])
    assert result == (3,1,1,1)

def test_empty_batch():
    assert summarize_reconciliation_direction([]).count == 0
