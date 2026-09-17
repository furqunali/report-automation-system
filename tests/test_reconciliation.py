from reporting_core.reconciliation import reconcile_sales

def test_reconcile_sales_accepts_tolerance():
    result = reconcile_sales(100, 100.005, tolerance=0.01)
    assert result.balanced is True
    assert result.delta == 0.004999999999995452

def test_reconcile_sales_flags_material_delta():
    assert reconcile_sales(100, 101, tolerance=0.01).balanced is False
