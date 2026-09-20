import pytest

from reporting_core.kpis import aggregate_kpis, product_breakdown, site_breakdown
from reporting_core.models import ReportRow


def row(site, product, sales):
    return ReportRow(site=site, product=product, sales=sales)


def test_aggregate_kpis_calculates_totals_and_leaders():
    rows = [row("A", "Widget", 10), row("A", "Gadget", 20), row("B", "Widget", 5)]
    result = aggregate_kpis(rows)
    assert result.rows == 3
    assert result.total_sales == 35
    assert result.average_sale == 11.67
    assert result.sites == 2
    assert result.products == 2
    assert result.top_site == "A"
    assert result.top_product == "Gadget"


def test_empty_aggregation_has_safe_defaults():
    result = aggregate_kpis([])
    assert result.rows == 0
    assert result.total_sales == 0
    assert result.average_sale == 0
    assert result.top_site is None
    assert result.top_product is None


def test_breakdowns_are_sorted_and_rounded():
    rows = [row("B", "X", 1.111), row("A", "X", 2.222), row("B", "Y", 3.333)]
    assert site_breakdown(rows) == {"A": 2.22, "B": 4.44}
    assert product_breakdown(rows) == {"X": 3.33, "Y": 3.33}


def test_invalid_rows_fail_fast():
    with pytest.raises(ValueError):
        aggregate_kpis([row("", "X", 1)])
