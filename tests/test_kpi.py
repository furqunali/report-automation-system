import pytest

from reporting_core.kpi import compute_management_kpis
from reporting_core.models import ReportRow


def row(site, product, quantity, sales, status="Active", category="General"):
    return ReportRow(
        site=site,
        category=category,
        product=product,
        quantity=quantity,
        sales=sales,
        status=status,
    )


# A small consolidated master reused across the exact-number assertions below.
#   Store A: Cola 100.00 (q10) + Chips 50.00 (q5) + Chips 30.00 (q3)
#   Store B: Cola 80.00 (q8)  + Bread 0.00 (q0, No Movement)
MASTER = [
    row("Store A", "Cola", 10, 100.00),
    row("Store A", "Chips", 5, 50.00),
    row("Store A", "Chips", 3, 30.00),
    row("Store B", "Cola", 8, 80.00),
    row("Store B", "Bread", 0, 0.00, status="No Movement"),
]


def test_company_totals_and_counts():
    kpis = compute_management_kpis(MASTER)
    assert kpis.row_count == 5
    assert kpis.total_sales == 260.00
    assert kpis.total_quantity == 26
    assert kpis.active_products == 4
    assert kpis.no_movement_products == 1
    assert kpis.site_count == 2
    assert kpis.product_count == 3  # Cola, Chips, Bread (distinct)


def test_per_location_subtotals_without_budget():
    kpis = compute_management_kpis(MASTER)
    by_site = {loc.site: loc for loc in kpis.locations}
    assert [loc.site for loc in kpis.locations] == ["Store A", "Store B"]

    a = by_site["Store A"]
    assert (a.sales, a.quantity, a.products) == (180.00, 18, 2)
    assert a.budget is None and a.variance is None and a.variance_pct is None

    b = by_site["Store B"]
    assert (b.sales, b.quantity, b.products) == (80.00, 8, 2)


def test_top_products_ranked_by_sales_then_name():
    kpis = compute_management_kpis(MASTER)
    assert [(p.product, p.sales, p.quantity) for p in kpis.top_products] == [
        ("Cola", 180.00, 18),
        ("Chips", 80.00, 8),
        ("Bread", 0.00, 0),
    ]


def test_top_n_limits_products():
    kpis = compute_management_kpis(MASTER, top_n=2)
    assert [p.product for p in kpis.top_products] == ["Cola", "Chips"]


def test_variance_vs_budget_including_a_non_reporting_site():
    budget = {"Store A": 200.0, "Store B": 100.0, "Store C": 150.0}
    kpis = compute_management_kpis(MASTER, budget=budget)

    assert kpis.total_budget == 450.00
    assert kpis.total_variance == -190.00
    assert kpis.total_variance_pct == -42.22  # -190 / 450 * 100

    by_site = {loc.site: loc for loc in kpis.locations}
    assert by_site["Store A"].variance == -20.00
    assert by_site["Store A"].variance_pct == -10.00
    assert by_site["Store B"].variance == -20.00
    assert by_site["Store B"].variance_pct == -20.00

    # Store C was budgeted but reported nothing: it must still surface.
    store_c = by_site["Store C"]
    assert store_c.sales == 0.00
    assert store_c.products == 0
    assert store_c.variance == -150.00
    assert store_c.variance_pct == -100.00
    # ...but it does not inflate the count of sites that actually reported.
    assert kpis.site_count == 2


def test_zero_budget_site_reports_variance_without_percentage():
    kpis = compute_management_kpis(
        [row("Store A", "Cola", 1, 25.00)],
        budget={"Store A": 0.0},
    )
    loc = kpis.locations[0]
    assert loc.budget == 0.0
    assert loc.variance == 25.00
    assert loc.variance_pct is None  # no divide-by-zero blow-up


def test_empty_master_is_safe():
    kpis = compute_management_kpis([])
    assert kpis.row_count == 0
    assert kpis.total_sales == 0
    assert kpis.total_budget is None
    assert kpis.total_variance is None
    assert kpis.locations == ()
    assert kpis.top_products == ()


def test_invalid_row_fails_fast():
    with pytest.raises(ValueError):
        compute_management_kpis([row("", "Cola", 1, 10.0)])


def test_bad_budget_value_is_rejected():
    with pytest.raises(ValueError):
        compute_management_kpis(MASTER, budget={"Store A": -5.0})


def test_top_n_must_be_positive():
    with pytest.raises(ValueError):
        compute_management_kpis(MASTER, top_n=0)
