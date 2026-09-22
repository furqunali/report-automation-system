from reporting_core.reconciliation import reconcile_sales
from reporting_core.reconciliation_metrics import build_reconciliation_metrics


def test_metrics_report_absolute_and_relative_delta():
    result = reconcile_sales(100, 102)
    metrics = build_reconciliation_metrics(result)
    assert metrics.absolute_delta == 2.0
    assert metrics.relative_delta == 0.02
    assert not metrics.within_tolerance

def test_metrics_use_none_relative_delta_for_zero_baseline():
    result = reconcile_sales(0, 0)
    metrics = build_reconciliation_metrics(result)
    assert metrics.relative_delta is None
    assert metrics.within_tolerance

def test_metrics_preserve_small_balanced_delta():
    result = reconcile_sales(10, 10.005)
    metrics = build_reconciliation_metrics(result)
    assert metrics.absolute_delta == 0.01
    assert metrics.within_tolerance
