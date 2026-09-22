from reporting_core.reconciliation import reconcile_sales
from reporting_core.reconciliation_signed_delta import mean_signed_delta


def test_mean_signed_delta_preserves_direction():
    results = [reconcile_sales(100,102), reconcile_sales(100,98)]
    assert mean_signed_delta(results) == 0.0

def test_mean_signed_delta_reports_positive_bias():
    results = [reconcile_sales(100,103), reconcile_sales(100,102)]
    assert mean_signed_delta(results) == 2.5

def test_mean_signed_delta_handles_empty_input():
    assert mean_signed_delta([]) == 0.0
