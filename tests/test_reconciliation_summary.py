from reporting_core.reconciliation_summary import summarize_reconciliation

def test_summary_marks_balanced_totals():
    result=summarize_reconciliation(10,10.005)
    assert result.balanced
    assert result.message=="sales totals balanced"

def test_summary_marks_unbalanced_totals():
    result=summarize_reconciliation(10,12)
    assert not result.balanced
    assert result.message=="sales totals require review"
