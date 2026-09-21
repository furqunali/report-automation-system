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


def test_reconciliation_rejects_nonfinite_values():
    import math
    for value in (math.nan, math.inf, -math.inf):
        try:
            reconcile_sales(value, 100)
        except ValueError:
            continue
        raise AssertionError("expected ValueError")


def test_reconciliation_rejects_invalid_tolerance():
    import math
    for tolerance in (math.nan, math.inf, -math.inf):
        try:
            reconcile_sales(100, 100, tolerance=tolerance)
        except ValueError:
            continue
        raise AssertionError("expected ValueError")

    try:
        reconcile_sales(100, 100, tolerance="0.01")
    except TypeError:
        pass
    else:
        raise AssertionError("expected TypeError")


def test_reconciliation_tolerance_is_absolute_only():
    result = reconcile_sales(1_000_000_000, 1_000_000_000.50, tolerance=0.01)
    assert result.balanced is False
