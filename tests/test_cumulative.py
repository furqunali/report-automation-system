import pytest

from reporting_core.cumulative import (
    Point,
    Running,
    running_stats,
    running_total,
)


def series(values, *, start=1):
    return [Point(f"P{start + i:02d}", float(v)) for i, v in enumerate(values)]


# --- running_stats: core behaviour -----------------------------------------


def test_running_total_accumulates():
    out = running_stats(series([10, 20, 30]))
    assert [r.cumulative for r in out] == [10.0, 30.0, 60.0]


def test_running_share_of_total():
    out = running_stats(series([25, 25, 50]))
    assert [r.running_share for r in out] == [25.0, 50.0, 100.0]


def test_running_max_and_min():
    out = running_stats(series([5, 2, 9, 1, 7]))
    assert [r.running_max for r in out] == [5.0, 5.0, 9.0, 9.0, 9.0]
    assert [r.running_min for r in out] == [5.0, 2.0, 2.0, 1.0, 1.0]


def test_single_point():
    out = running_stats(series([42]))
    assert out[0].cumulative == 42.0
    assert out[0].running_share == 100.0
    assert out[0].running_max == 42.0 and out[0].running_min == 42.0


def test_result_length_and_order_preserved():
    pts = series([1, 2, 3, 4])
    out = running_stats(pts)
    assert len(out) == len(pts)
    assert [r.label for r in out] == [p.label for p in pts]
    assert all(isinstance(r, Running) for r in out)


def test_rounding_applied():
    out = running_stats(series([1, 1, 1]), digits=2)
    # each share = 1/3, 2/3, 3/3 of total 3 -> 33.33, 66.67, 100.0
    assert [r.running_share for r in out] == [33.33, 66.67, 100.0]


def test_negative_values_supported():
    out = running_stats(series([-10, 5, -3]))
    assert [r.cumulative for r in out] == [-10.0, -5.0, -8.0]
    assert out[-1].running_min == -10.0
    assert out[-1].running_max == 5.0


# --- running_share edge cases ----------------------------------------------


def test_zero_grand_total_share_is_none():
    # values cancel to a zero grand total -> no defined share, never div-by-zero
    out = running_stats(series([10, -10]))
    assert all(r.running_share is None for r in out)


def test_mixed_sign_share_can_exceed_100():
    # cumulative can overshoot the (smaller) grand total; faithful, not a bug
    out = running_stats(series([100, -50]))
    # grand total = 50; after first point cumulative 100 -> 200% share
    assert out[0].running_share == 200.0
    assert out[1].running_share == 100.0


def test_empty_series_returns_empty():
    assert running_stats([]) == ()


# --- running_total projection ----------------------------------------------


def test_running_total_helper():
    assert running_total(series([1, 2, 3])) == (1.0, 3.0, 6.0)


def test_running_total_empty():
    assert running_total([]) == ()


# --- validation ------------------------------------------------------------


def test_rejects_non_point():
    with pytest.raises(TypeError):
        running_stats([(1, 2.0)])


def test_rejects_duplicate_labels():
    with pytest.raises(ValueError):
        running_stats([Point("P01", 1.0), Point("P01", 2.0)])


def test_rejects_empty_label():
    with pytest.raises(ValueError):
        running_stats([Point("   ", 1.0)])


def test_rejects_boolean_value():
    with pytest.raises(TypeError):
        running_stats([Point("P01", True)])


def test_rejects_non_finite_value():
    with pytest.raises(ValueError):
        running_stats([Point("P01", float("inf"))])


def test_digits_must_be_non_negative():
    with pytest.raises(ValueError):
        running_stats(series([1, 2]), digits=-1)


def test_digits_must_be_int_not_bool():
    with pytest.raises(TypeError):
        running_stats(series([1, 2]), digits=True)
