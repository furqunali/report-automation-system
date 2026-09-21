from reporting_core.reconciliation import reconcile_sales
from reporting_core.reconciliation_batch import summarize_reconciliations

def test_batch_summary_counts_balance_and_delta():
    s = summarize_reconciliations([reconcile_sales(100,100), reconcile_sales(50,52)])
    assert (s.count, s.balanced, s.unbalanced, s.total_absolute_delta) == (2,1,1,2.0)

def test_batch_summary_handles_empty_input():
    assert summarize_reconciliations([]).count == 0
