from dataclasses import FrozenInstanceError

import pytest

from reporting_core.models import ReportRow
from reporting_core.pivot import Pivot, PivotGroup, pivot, top_groups


def row(
    *,
    site="Site A",
    category="Snacks",
    product="Chips",
    quantity=2.0,
    sales=10.0,
    status="Active",
):
    return ReportRow(site, category, product, quantity, sales, status)


def _as_dict(result):
    """Collapse a pivot into ``{key: (count, value)}`` for easy assertions."""
    return {g.key: (g.count, g.value) for g in result.groups}


# --- basic grouping / aggregation -----------------------------------------


def test_sum_by_single_dimension():
    rows = [
        row(site="A", sales=10),
        row(site="A", sales=5),
        row(site="B", sales=7),
    ]
    result = pivot(rows, by="site", metric="sales", agg="sum")
    assert isinstance(result, Pivot)
    assert result.by == ("site",)
    assert result.metric == "sales"
    assert result.agg == "sum"
    assert _as_dict(result) == {("A",): (2, 15.0), ("B",): (1, 7.0)}


def test_default_agg_is_sum():
    rows = [row(site="A", sales=3), row(site="A", sales=4)]
    result = pivot(rows, by="site", metric="sales")
    assert result.agg == "sum"
    assert _as_dict(result) == {("A",): (2, 7.0)}


def test_mean_is_rounded_to_two_decimals():
    rows = [row(site="A", sales=10), row(site="A", sales=11), row(site="A", sales=11)]
    result = pivot(rows, by="site", metric="sales", agg="mean")
    # (10 + 11 + 11) / 3 = 10.6666... -> 10.67
    assert _as_dict(result) == {("A",): (3, 10.67)}


def test_min_and_max():
    rows = [row(site="A", sales=10), row(site="A", sales=3), row(site="A", sales=99)]
    assert _as_dict(pivot(rows, by="site", metric="sales", agg="min")) == {("A",): (3, 3.0)}
    assert _as_dict(pivot(rows, by="site", metric="sales", agg="max")) == {("A",): (3, 99.0)}


def test_count_tallies_rows_and_needs_no_metric():
    rows = [row(site="A"), row(site="A"), row(site="B")]
    result = pivot(rows, by="site", agg="count")
    assert result.metric is None
    groups = _as_dict(result)
    assert groups == {("A",): (2, 2.0), ("B",): (1, 1.0)}
    # For a count pivot the value always equals the count.
    for g in result.groups:
        assert g.value == float(g.count)


def test_quantity_metric_supported():
    rows = [row(site="A", quantity=2), row(site="A", quantity=5)]
    result = pivot(rows, by="site", metric="quantity", agg="sum")
    assert _as_dict(result) == {("A",): (2, 7.0)}


# --- multi-dimension grouping ---------------------------------------------


def test_group_by_two_dimensions_uses_tuple_key_in_order():
    rows = [
        row(site="A", category="Snacks", sales=10),
        row(site="A", category="Drinks", sales=4),
        row(site="A", category="Snacks", sales=6),
        row(site="B", category="Drinks", sales=8),
    ]
    result = pivot(rows, by=["site", "category"], metric="sales", agg="sum")
    assert result.by == ("site", "category")
    assert _as_dict(result) == {
        ("A", "Snacks"): (2, 16.0),
        ("A", "Drinks"): (1, 4.0),
        ("B", "Drinks"): (1, 8.0),
    }


def test_group_by_status_dimension():
    rows = [
        row(status="Active", sales=10),
        row(status="No Movement", sales=0),
        row(status="Active", sales=5),
    ]
    result = pivot(rows, by="status", metric="sales", agg="sum")
    assert _as_dict(result) == {("Active",): (2, 15.0), ("No Movement",): (1, 0.0)}


# --- determinism ----------------------------------------------------------


def test_groups_sorted_ascending_by_key():
    rows = [row(site=s) for s in ("C", "A", "B", "A")]
    result = pivot(rows, by="site", agg="count")
    keys = [g.key for g in result.groups]
    assert keys == sorted(keys)
    assert keys == [("A",), ("B",), ("C",)]


def test_single_dimension_key_is_still_a_tuple():
    result = pivot([row(site="Solo")], by="site", agg="count")
    assert result.groups[0].key == ("Solo",)


def test_empty_rows_yields_no_groups_but_validates_args():
    result = pivot([], by="site", metric="sales", agg="sum")
    assert result.groups == ()
    assert result.by == ("site",)
    # Argument validation still runs on an empty master.
    with pytest.raises(ValueError):
        pivot([], by="site", metric="profit", agg="sum")


# --- top_groups -----------------------------------------------------------


def test_top_groups_ranks_by_value_desc():
    rows = [
        row(site="A", sales=10),
        row(site="B", sales=30),
        row(site="C", sales=20),
    ]
    result = pivot(rows, by="site", metric="sales", agg="sum")
    top = top_groups(result, top_n=2)
    assert [g.key for g in top] == [("B",), ("C",)]


def test_top_groups_breaks_ties_by_key():
    rows = [row(site="B", sales=10), row(site="A", sales=10), row(site="C", sales=5)]
    result = pivot(rows, by="site", metric="sales", agg="sum")
    top = top_groups(result, top_n=3)
    # A and B tie on 10.0 -> A first (key ascending); C last.
    assert [g.key for g in top] == [("A",), ("B",), ("C",)]


def test_top_groups_rejects_bad_top_n():
    result = pivot([row()], by="site", agg="count")
    with pytest.raises(ValueError):
        top_groups(result, top_n=0)
    with pytest.raises(ValueError):
        top_groups(result, top_n=True)


# --- validation -----------------------------------------------------------


def test_unknown_dimension_rejected():
    with pytest.raises(ValueError):
        pivot([row()], by="region", agg="count")


def test_empty_by_rejected():
    with pytest.raises(ValueError):
        pivot([row()], by=[], agg="count")


def test_duplicate_dimension_rejected():
    with pytest.raises(ValueError):
        pivot([row()], by=["site", "site"], agg="count")


def test_by_wrong_type_rejected():
    with pytest.raises(TypeError):
        pivot([row()], by=123, agg="count")


def test_unknown_agg_rejected():
    with pytest.raises(ValueError):
        pivot([row()], by="site", metric="sales", agg="median")


def test_metric_required_for_non_count_agg():
    with pytest.raises(ValueError):
        pivot([row()], by="site", agg="sum")


def test_metric_forbidden_for_count_agg():
    with pytest.raises(ValueError):
        pivot([row()], by="site", metric="sales", agg="count")


def test_unknown_metric_rejected():
    with pytest.raises(ValueError):
        pivot([row()], by="site", metric="profit", agg="sum")


def test_invalid_rows_fail_fast():
    bad = row()
    object.__setattr__(bad, "sales", -1.0)
    with pytest.raises(ValueError):
        pivot([bad, row()], by="site", metric="sales", agg="sum")


def test_pivot_group_is_frozen():
    g = PivotGroup(key=("A",), count=1, value=1.0)
    with pytest.raises(FrozenInstanceError):
        g.value = 2.0  # type: ignore[misc]
