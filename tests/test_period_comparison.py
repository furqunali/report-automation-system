import pytest

from reporting_core.kpi import compute_management_kpis
from reporting_core.models import ReportRow
from reporting_core.period_comparison import (
    LocationDelta,
    MetricDelta,
    PeriodComparison,
    compare_periods,
    top_movers,
)


def row(site, product, quantity, sales, status="Active", category="General"):
    return ReportRow(
        site=site,
        category=category,
        product=product,
        quantity=quantity,
        sales=sales,
        status=status,
    )


# Previous month: Store A 100.00 (q10), Store B 80.00 (q8).
PREVIOUS = compute_management_kpis(
    [
        row("Store A", "Cola", 10, 100.00),
        row("Store B", "Cola", 8, 80.00),
    ]
)

# Current month: Store A grows to 150.00 (q15), Store B falls to 60.00 (q6),
# Store C is brand new at 40.00 (q4). Store B still reports.
CURRENT = compute_management_kpis(
    [
        row("Store A", "Cola", 15, 150.00),
        row("Store B", "Cola", 6, 60.00),
        row("Store C", "Cola", 4, 40.00),
    ]
)


def _metric(comparison, name):
    return next(m for m in comparison.metrics if m.metric == name)


def _loc(comparison, site):
    return next(loc for loc in comparison.locations if loc.site == site)


def test_returns_period_comparison_with_labels():
    cmp = compare_periods(CURRENT, PREVIOUS, current_label="2026-09", previous_label="2026-08")
    assert isinstance(cmp, PeriodComparison)
    assert cmp.current_label == "2026-09"
    assert cmp.previous_label == "2026-08"


def test_scalar_metric_delta_and_pct_change():
    cmp = compare_periods(CURRENT, PREVIOUS)
    sales = _metric(cmp, "total_sales")
    assert isinstance(sales, MetricDelta)
    # current 250.00 vs previous 180.00
    assert sales.current == 250.00
    assert sales.previous == 180.00
    assert sales.delta == 70.00
    assert sales.pct_change == 38.89  # 70 / 180 * 100

    qty = _metric(cmp, "total_quantity")
    assert (qty.current, qty.previous, qty.delta) == (25, 18, 7)

    sites = _metric(cmp, "site_count")
    assert (sites.current, sites.previous, sites.delta) == (3, 2, 1)


def test_all_headline_metrics_present_in_fixed_order():
    cmp = compare_periods(CURRENT, PREVIOUS)
    assert [m.metric for m in cmp.metrics] == [
        "total_sales",
        "total_quantity",
        "active_products",
        "no_movement_products",
        "site_count",
        "product_count",
    ]


def test_continuing_location_up_and_down():
    cmp = compare_periods(CURRENT, PREVIOUS)
    a = _loc(cmp, "Store A")
    assert isinstance(a, LocationDelta)
    assert a.presence == "continuing"
    assert (a.previous_sales, a.current_sales, a.sales_delta) == (100.00, 150.00, 50.00)
    assert a.sales_pct_change == 50.00
    assert (a.previous_quantity, a.current_quantity, a.quantity_delta) == (10, 15, 5)

    b = _loc(cmp, "Store B")
    assert b.presence == "continuing"
    assert (b.previous_sales, b.current_sales, b.sales_delta) == (80.00, 60.00, -20.00)
    assert b.sales_pct_change == -25.00  # -20 / 80 * 100


def test_new_location_has_no_percent_change():
    cmp = compare_periods(CURRENT, PREVIOUS)
    c = _loc(cmp, "Store C")
    assert c.presence == "new"
    assert c.previous_sales == 0.00
    assert c.current_sales == 40.00
    assert c.sales_delta == 40.00
    # Growth from a zero base is undefined, not "inf%".
    assert c.sales_pct_change is None
    assert c.quantity_pct_change is None


def test_dropped_location_is_carried_through():
    # A store that reported last month but not this month must not vanish.
    prev = compute_management_kpis([row("Store A", "Cola", 5, 50.00), row("Gone", "Cola", 2, 20.00)])
    cur = compute_management_kpis([row("Store A", "Cola", 5, 50.00)])
    cmp = compare_periods(cur, prev)
    gone = _loc(cmp, "Gone")
    assert gone.presence == "dropped"
    assert gone.previous_sales == 20.00
    assert gone.current_sales == 0.00
    assert gone.sales_delta == -20.00
    assert gone.sales_pct_change == -100.00


def test_flat_zero_location_reports_zero_percent():
    prev = compute_management_kpis([row("Store A", "Cola", 0, 0.00, status="No Movement")])
    cur = compute_management_kpis([row("Store A", "Cola", 0, 0.00, status="No Movement")])
    cmp = compare_periods(cur, prev)
    a = _loc(cmp, "Store A")
    assert a.sales_pct_change == 0.0  # 0 -> 0 is flat, not undefined
    assert a.sales_delta == 0.0


def test_locations_sorted_by_site_name():
    cmp = compare_periods(CURRENT, PREVIOUS)
    assert [loc.site for loc in cmp.locations] == ["Store A", "Store B", "Store C"]


def test_top_movers_ranked_by_absolute_swing():
    cmp = compare_periods(CURRENT, PREVIOUS)
    movers = top_movers(cmp, top_n=2)
    # Store A +50 (biggest), then Store C +40, then Store B -20.
    assert [m.site for m in movers] == ["Store A", "Store C"]


def test_top_movers_excludes_flat_sites_and_breaks_ties_by_name():
    # Two sites move by the same magnitude; a third does not move at all.
    prev = compute_management_kpis(
        [row("Alpha", "Cola", 1, 100.00), row("Beta", "Cola", 1, 50.00), row("Flat", "Cola", 1, 10.00)]
    )
    cur = compute_management_kpis(
        [row("Alpha", "Cola", 1, 90.00), row("Beta", "Cola", 1, 60.00), row("Flat", "Cola", 1, 10.00)]
    )
    cmp = compare_periods(cur, prev)
    movers = top_movers(cmp)
    # Alpha -10 and Beta +10 tie on magnitude -> alphabetical; Flat excluded.
    assert [m.site for m in movers] == ["Alpha", "Beta"]


def test_top_movers_requires_positive_top_n():
    cmp = compare_periods(CURRENT, PREVIOUS)
    with pytest.raises(ValueError):
        top_movers(cmp, top_n=0)


def test_wrong_argument_type_is_rejected():
    with pytest.raises(TypeError):
        compare_periods(CURRENT, {"total_sales": 1})
    with pytest.raises(TypeError):
        compare_periods("not-a-report", PREVIOUS)


def test_labels_must_be_non_empty_and_distinct():
    with pytest.raises(ValueError):
        compare_periods(CURRENT, PREVIOUS, current_label="   ")
    with pytest.raises(ValueError):
        compare_periods(CURRENT, PREVIOUS, current_label="2026-09", previous_label="2026-09")


def test_empty_reports_compare_cleanly():
    empty = compute_management_kpis([])
    cmp = compare_periods(empty, empty)
    assert cmp.locations == ()
    sales = _metric(cmp, "total_sales")
    assert sales.current == 0 and sales.previous == 0 and sales.delta == 0
    assert sales.pct_change == 0.0
    assert top_movers(cmp) == ()
