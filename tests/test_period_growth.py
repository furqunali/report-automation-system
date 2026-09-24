import pytest

from reporting_core.period_growth import (
    Growth,
    Period,
    growth_series,
    pct_change,
)


def series(values, *, start=1):
    """Build a time-ordered series with sequential ``P01``-style labels."""
    return [Period(f"P{start + i:02d}", v) for i, v in enumerate(values)]


# --- growth_series: core behaviour -----------------------------------------


def test_period_over_period_simple():
    out = growth_series(series([100, 110, 121]), periods_per_year=12)
    assert [g.pop_pct for g in out] == [None, 10.0, 10.0]
    assert out[0].prev_value is None


def test_pop_can_be_negative():
    out = growth_series(series([200, 150]))
    assert out[1].pop_pct == -25.0


def test_prior_year_growth():
    # 13 monthly points; point 13 compares against point 1 (12 back).
    out = growth_series(series([100] * 12 + [125]), periods_per_year=12)
    assert out[-1].yoy_pct == 25.0
    assert out[-1].prior_year_value == 100.0
    # Everything before index 12 has no prior-year baseline.
    assert all(g.yoy_pct is None for g in out[:12])


def test_quarterly_periods_per_year():
    out = growth_series(series([10, 11, 12, 13, 20]), periods_per_year=4)
    # index 4 compares against index 0 (10 -> 20 = +100%).
    assert out[4].yoy_pct == 100.0


def test_result_length_and_order_preserved():
    pts = series([1, 2, 3, 4])
    out = growth_series(pts)
    assert len(out) == len(pts)
    assert [g.label for g in out] == [p.label for p in pts]
    assert all(isinstance(g, Growth) for g in out)


def test_rounding_of_percentages():
    out = growth_series(series([3, 4]), digits=2)
    # (4-3)/3*100 = 33.333... -> 33.33
    assert out[1].pop_pct == 33.33


def test_negative_baseline_sign_tracks_direction():
    # baseline -100, current -50: value rose, so growth is positive.
    out = growth_series(series([-100, -50]))
    assert out[1].pop_pct == 50.0


# --- growth_series: safe baselines -----------------------------------------


def test_zero_baseline_yields_none_not_infinity():
    out = growth_series(series([0, 50]))
    assert out[1].pop_pct is None


def test_none_value_baseline_yields_none():
    out = growth_series([Period("P01", None), Period("P02", 50.0)])
    assert out[1].pop_pct is None
    assert out[1].prev_value is None


def test_none_current_value_yields_none():
    out = growth_series([Period("P01", 50.0), Period("P02", None)])
    assert out[1].value is None
    assert out[1].pop_pct is None


def test_empty_series_returns_empty():
    assert growth_series([]) == ()


def test_flat_is_zero_not_none():
    out = growth_series(series([100, 100]))
    assert out[1].pop_pct == 0.0  # genuinely flat, distinct from None


# --- validation ------------------------------------------------------------


def test_rejects_non_period_series():
    with pytest.raises(TypeError):
        growth_series([(1, 2.0)])


def test_rejects_duplicate_labels():
    with pytest.raises(ValueError):
        growth_series([Period("P01", 1.0), Period("P01", 2.0)])


def test_rejects_empty_label():
    with pytest.raises(ValueError):
        growth_series([Period("  ", 1.0)])


def test_rejects_boolean_value():
    with pytest.raises(TypeError):
        growth_series([Period("P01", True)])


def test_rejects_non_finite_value():
    with pytest.raises(ValueError):
        growth_series([Period("P01", float("nan"))])


def test_periods_per_year_must_be_positive():
    with pytest.raises(ValueError):
        growth_series(series([1, 2]), periods_per_year=0)


def test_periods_per_year_must_be_int_not_bool():
    with pytest.raises(TypeError):
        growth_series(series([1, 2]), periods_per_year=True)


def test_digits_must_be_non_negative():
    with pytest.raises(ValueError):
        growth_series(series([1, 2]), digits=-1)


# --- pct_change one-shot ---------------------------------------------------


def test_pct_change_basic():
    assert pct_change(110, 100) == 10.0


def test_pct_change_zero_baseline_is_none():
    assert pct_change(50, 0) is None


def test_pct_change_none_operand_is_none():
    assert pct_change(None, 100) is None
    assert pct_change(100, None) is None


def test_pct_change_rejects_bool():
    with pytest.raises(TypeError):
        pct_change(True, 100)


def test_pct_change_rejects_non_finite():
    with pytest.raises(ValueError):
        pct_change(float("inf"), 100)
