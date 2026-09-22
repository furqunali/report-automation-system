import pytest

from reporting_core.models import ReportRow
from reporting_core.outliers import IQRBounds, find_outliers, iqr_bounds


def row(sales=10.0, quantity=2.0, *, site="Site A", product="Product", status="Active"):
    return ReportRow(site, "Category", product, quantity, sales, status)


# --- iqr_bounds ------------------------------------------------------------


def test_iqr_bounds_matches_linear_interpolation():
    # For 1..9 the type-7 quartiles are Q1=3, median=5, Q3=7 -> IQR=4.
    bounds = iqr_bounds([9, 1, 5, 3, 7, 2, 4, 6, 8])
    assert isinstance(bounds, IQRBounds)
    assert bounds.q1 == 3.0
    assert bounds.median == 5.0
    assert bounds.q3 == 7.0
    assert bounds.iqr == 4.0
    assert bounds.lower == 3.0 - 1.5 * 4.0
    assert bounds.upper == 7.0 + 1.5 * 4.0


def test_iqr_bounds_single_value_has_zero_iqr():
    bounds = iqr_bounds([42.0])
    assert bounds.q1 == bounds.median == bounds.q3 == 42.0
    assert bounds.iqr == 0.0
    assert bounds.lower == bounds.upper == 42.0


def test_iqr_bounds_k_widens_fences():
    tight = iqr_bounds([1, 2, 3, 4, 5], k=1.5)
    wide = iqr_bounds([1, 2, 3, 4, 5], k=3.0)
    assert wide.lower < tight.lower
    assert wide.upper > tight.upper


def test_iqr_bounds_rejects_empty():
    with pytest.raises(ValueError):
        iqr_bounds([])


def test_iqr_bounds_rejects_negative_k():
    with pytest.raises(ValueError):
        iqr_bounds([1, 2, 3], k=-1)


def test_iqr_bounds_rejects_non_numeric_k():
    with pytest.raises(TypeError):
        iqr_bounds([1, 2, 3], k="wide")


def test_iqr_bounds_rejects_boolean_values():
    with pytest.raises(TypeError):
        iqr_bounds([1, 2, True])


def test_iqr_bounds_rejects_non_finite_values():
    with pytest.raises(ValueError):
        iqr_bounds([1.0, 2.0, float("inf")])


# --- find_outliers ---------------------------------------------------------


def test_flags_high_sales_outlier():
    rows = [row(sales=v) for v in (9, 10, 11, 10, 9, 11, 10, 10)] + [row(sales=1000, product="Spike")]
    found = find_outliers(rows)
    assert len(found) == 1
    hit = found[0]
    assert hit.row_index == len(rows) - 1
    assert hit.product == "Spike"
    assert hit.side == "high"
    assert hit.severity == "extreme"
    assert hit.value == 1000.0
    assert hit.metric == "sales"


def test_flags_low_outlier_side():
    rows = [row(sales=v) for v in (100, 101, 99, 100, 102, 98)] + [row(sales=1, product="Dip")]
    found = find_outliers(rows)
    assert len(found) == 1
    assert found[0].side == "low"
    assert found[0].product == "Dip"


def test_tight_distribution_has_no_outliers():
    rows = [row(sales=v) for v in (10, 11, 9, 10, 12, 8, 11, 10, 9, 10)]
    assert find_outliers(rows) == []


def test_value_on_the_fence_is_not_flagged():
    # 11 identical values -> IQR=0, both fences collapse onto 10.0. A value
    # sitting exactly on the fence must not flag; only strictly-beyond does.
    rows = [row(sales=10.0) for _ in range(10)] + [row(sales=10.0, product="OnFence")]
    assert find_outliers(rows) == []
    rows.append(row(sales=10.5, product="Above"))
    found = find_outliers(rows)
    assert [item.product for item in found] == ["Above"]


def test_mild_vs_extreme_severity():
    base = [row(sales=v) for v in (10, 11, 9, 10, 12, 8, 11, 10)]
    # Q1~9.75 Q3~11 IQR~1.25 -> mild fence upper ~12.9, extreme fence ~14.75.
    mild = find_outliers(base + [row(sales=13, product="Mild")])
    assert mild[-1].severity == "mild"
    strong = find_outliers(base + [row(sales=40, product="Strong")])
    assert strong[-1].severity == "extreme"


def test_small_sample_is_skipped():
    # Four points with an obvious spike: evaluated at the default min_points=4,
    # but skipped entirely when min_points demands a larger sample.
    rows = [row(sales=10), row(sales=10), row(sales=10), row(sales=1000, product="Spike")]
    assert find_outliers(rows, min_points=5) == []
    flagged = find_outliers(rows)
    assert [item.product for item in flagged] == ["Spike"]


def test_quantity_metric_is_supported():
    rows = [row(quantity=v) for v in (2, 3, 2, 3, 2, 3)] + [row(quantity=500, product="Q")]
    found = find_outliers(rows, metric="quantity")
    assert len(found) == 1
    assert found[0].metric == "quantity"
    assert found[0].product == "Q"


def test_constant_column_flags_only_the_deviant():
    rows = [row(sales=5.0) for _ in range(6)] + [row(sales=6.0, product="Odd")]
    found = find_outliers(rows)
    # IQR is zero; fences collapse onto 5.0, so the lone 6.0 is beyond upper.
    assert len(found) == 1
    assert found[0].product == "Odd"
    assert found[0].side == "high"


def test_results_sorted_by_row_index():
    rows = [row(sales=1, product="First")]
    rows += [row(sales=10) for _ in range(10)]
    rows += [row(sales=2000, product="Last")]
    found = find_outliers(rows)
    indexes = [item.row_index for item in found]
    assert indexes == sorted(indexes)
    assert len(found) == 2
    assert indexes[0] == 0
    assert indexes[-1] == len(rows) - 1


def test_invalid_metric_rejected():
    with pytest.raises(ValueError):
        find_outliers([row()], metric="profit")


def test_min_points_must_be_at_least_two():
    with pytest.raises(ValueError):
        find_outliers([row()], min_points=1)


def test_extreme_k_must_not_be_below_k():
    with pytest.raises(ValueError):
        find_outliers([row(sales=v) for v in range(1, 10)], k=3.0, extreme_k=1.5)


def test_invalid_rows_fail_fast():
    bad = row()
    object.__setattr__(bad, "sales", -1.0)
    with pytest.raises(ValueError):
        find_outliers([bad] + [row() for _ in range(5)])
