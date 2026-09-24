import pytest

from reporting_core.moving_average import (
    Crossover,
    RollingWindow,
    TrendPoint,
    crossovers,
    rolling_average,
)


def series(values, *, start=1):
    """Build a time-ordered series with sequential ``YYYY-MM``-ish labels."""
    return [TrendPoint(f"P{start + i:02d}", float(v)) for i, v in enumerate(values)]


# --- rolling_average: core behaviour ---------------------------------------


def test_trailing_average_over_full_windows():
    windows = rolling_average(series([10, 20, 30, 40]), window=2)
    assert [w.average for w in windows] == [None, 15.0, 25.0, 35.0]
    assert [w.window_size for w in windows] == [1, 2, 2, 2]
    # The first point never has a full 2-point window, so no average.
    assert windows[0].average is None and windows[0].delta is None


def test_window_size_grows_then_holds_steady():
    windows = rolling_average(series([1, 2, 3, 4, 5]), window=3, min_periods=1)
    assert [w.window_size for w in windows] == [1, 2, 3, 3, 3]
    # min_periods=1 means every point gets an average, growing then trailing-3.
    assert [w.average for w in windows] == [1.0, 1.5, 2.0, 3.0, 4.0]


def test_delta_is_value_minus_average():
    windows = rolling_average(series([10, 10, 40]), window=3, min_periods=1)
    last = windows[-1]
    # trailing-3 mean of 10,10,40 = 20.0; value 40 sits +20 above trend.
    assert last.average == 20.0
    assert last.delta == 20.0
    assert windows[0].delta == 0.0  # single point equals its own average


def test_window_one_is_the_raw_series():
    values = [3, 7, 2, 9]
    windows = rolling_average(series(values), window=1)
    assert [w.average for w in windows] == [float(v) for v in values]
    assert all(w.delta == 0.0 for w in windows)
    assert all(w.window_size == 1 for w in windows)


def test_min_periods_defaults_to_window():
    windows = rolling_average(series([5, 5, 5, 5]), window=3)
    assert [w.average for w in windows] == [None, None, 5.0, 5.0]


def test_min_periods_allows_partial_warmup():
    windows = rolling_average(series([2, 4, 6, 8]), window=3, min_periods=2)
    assert windows[0].average is None
    assert windows[1].average == 3.0  # mean(2,4)
    assert windows[2].average == 4.0  # mean(2,4,6)
    assert windows[3].average == 6.0  # mean(4,6,8) trailing-3


def test_values_and_averages_are_rounded():
    windows = rolling_average(series([1, 2]), window=2)
    # mean(1,2)=1.5 exactly; use thirds to force rounding.
    windows = rolling_average(series([1, 1, 2]), window=3)
    assert windows[-1].average == 1.33
    assert windows[-1].delta == 0.67


def test_result_length_and_order_preserved():
    pts = series([9, 8, 7, 6, 5])
    windows = rolling_average(pts, window=2)
    assert len(windows) == len(pts)
    assert [w.period for w in windows] == [p.period for p in pts]
    assert all(isinstance(w, RollingWindow) for w in windows)


def test_empty_series_returns_empty():
    assert rolling_average([], window=3) == ()


def test_negative_values_are_supported():
    windows = rolling_average(series([-10, -20, -30]), window=2)
    assert windows[1].average == -15.0
    assert windows[2].average == -25.0


# --- rolling_average: validation -------------------------------------------


def test_window_must_be_positive():
    with pytest.raises(ValueError):
        rolling_average(series([1, 2]), window=0)


def test_window_must_be_int_not_bool():
    with pytest.raises(TypeError):
        rolling_average(series([1, 2]), window=True)


def test_window_must_be_numeric():
    with pytest.raises(TypeError):
        rolling_average(series([1, 2]), window=2.0)


def test_min_periods_cannot_exceed_window():
    with pytest.raises(ValueError):
        rolling_average(series([1, 2, 3]), window=2, min_periods=3)


def test_min_periods_must_be_positive():
    with pytest.raises(ValueError):
        rolling_average(series([1, 2, 3]), window=2, min_periods=0)


def test_rejects_non_trendpoint_series():
    with pytest.raises(TypeError):
        rolling_average([(1, 2.0)], window=1)


def test_rejects_empty_period_label():
    with pytest.raises(ValueError):
        rolling_average([TrendPoint("  ", 1.0)], window=1)


def test_rejects_duplicate_periods():
    with pytest.raises(ValueError):
        rolling_average([TrendPoint("2026-01", 1.0), TrendPoint("2026-01", 2.0)], window=1)


def test_rejects_boolean_value():
    with pytest.raises(TypeError):
        rolling_average([TrendPoint("P01", True)], window=1)


def test_rejects_non_finite_value():
    with pytest.raises(ValueError):
        rolling_average([TrendPoint("P01", float("inf"))], window=1)


# --- crossovers ------------------------------------------------------------


def test_crossover_up_and_down():
    # Values oscillate around a smooth trend, forcing the raw line to cross.
    windows = rolling_average(series([10, 10, 20, 5, 20]), window=3, min_periods=1)
    crosses = crossovers(windows)
    dirs = [(c.period, c.direction) for c in crosses]
    # value-minus-trailing-avg per point: 0, 0, +6.67(above), -6.67(below),
    # +5(above) -> the side flips twice: below at P04, then above at P05.
    assert dirs == [("P04", "below"), ("P05", "above")]


def test_no_crossover_on_monotonic_rise():
    # A strictly rising series keeps the raw value above its trailing average
    # once warm; it never flips sides.
    windows = rolling_average(series([1, 2, 3, 4, 5]), window=2, min_periods=1)
    assert crossovers(windows) == ()


def test_crossover_ignores_warmup_none_averages():
    windows = rolling_average(series([10, 30, 5, 30]), window=3)
    # Only P03 and P04 have averages (window=3, min_periods=3 default),
    # so only one adjacent pair is comparable -> at most one crossover.
    crosses = crossovers(windows)
    assert all(isinstance(c, Crossover) for c in crosses)
    assert all(c.period in {"P03", "P04"} for c in crosses)


def test_flat_period_does_not_trigger_or_reset():
    # value exactly on its average (delta==0) is neither above nor below and
    # must not fabricate a crossover nor reset the last-known side.
    windows = (
        RollingWindow("A", 12.0, 10.0, 3, 2.0),   # above
        RollingWindow("B", 10.0, 10.0, 3, 0.0),   # exactly on average
        RollingWindow("C", 13.0, 10.0, 3, 3.0),   # still above -> no crossover
    )
    assert crossovers(windows) == ()


def test_flat_period_between_reversal_still_crosses():
    windows = (
        RollingWindow("A", 12.0, 10.0, 3, 2.0),   # above
        RollingWindow("B", 10.0, 10.0, 3, 0.0),   # flat: side preserved
        RollingWindow("C", 7.0, 10.0, 3, -3.0),   # below -> crossover
    )
    crosses = crossovers(windows)
    assert [(c.period, c.direction) for c in crosses] == [("C", "below")]


def test_crossover_carries_value_and_average():
    windows = (
        RollingWindow("A", 20.0, 10.0, 2, 10.0),
        RollingWindow("B", 4.0, 10.0, 2, -6.0),
    )
    crosses = crossovers(windows)
    assert len(crosses) == 1
    assert crosses[0].value == 4.0
    assert crosses[0].average == 10.0
    assert crosses[0].direction == "below"


def test_crossovers_rejects_non_rollingwindow():
    with pytest.raises(TypeError):
        crossovers((("A", 1.0, 1.0, 1, 0.0),))


def test_crossovers_empty_input():
    assert crossovers(()) == ()
