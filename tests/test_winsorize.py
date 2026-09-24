import pytest

from reporting_core.winsorize import (
    WinsorizeResult,
    percentile,
    winsorize,
)


# --- percentile ------------------------------------------------------------


def test_percentile_min_and_max():
    data = [1, 2, 3, 4, 5]
    assert percentile(data, 0) == 1.0
    assert percentile(data, 100) == 5.0


def test_percentile_median():
    assert percentile([1, 2, 3, 4, 5], 50) == 3.0


def test_percentile_interpolates():
    # type-7: for [0,10] the 25th percentile is 2.5
    assert percentile([0, 10], 25) == 2.5


def test_percentile_single_value():
    assert percentile([7], 42) == 7.0


def test_percentile_rejects_out_of_range():
    with pytest.raises(ValueError):
        percentile([1, 2, 3], 150)


# --- winsorize: core behaviour ---------------------------------------------


def test_clips_both_tails():
    data = list(range(1, 101))  # 1..100
    res = winsorize(data, lower_percentile=5, upper_percentile=95)
    assert isinstance(res, WinsorizeResult)
    # nothing exceeds the bounds after clipping
    assert min(res.clipped) == res.lower_bound
    assert max(res.clipped) == res.upper_bound
    assert res.clipped_low > 0 and res.clipped_high > 0


def test_length_and_order_preserved():
    data = [5, 1, 100, 3, 2]
    res = winsorize(data, lower_percentile=10, upper_percentile=90)
    assert len(res.clipped) == len(data)


def test_counts_moved_at_each_end():
    data = [0, 10, 20, 30, 40, 50, 60, 70, 80, 1000]
    res = winsorize(data, lower_percentile=10, upper_percentile=90)
    # the lone 1000 is above the 90th percentile and gets pulled down
    assert res.clipped_high >= 1
    assert max(res.clipped) == res.upper_bound


def test_value_on_bound_not_counted():
    data = [10, 10, 10, 10]
    res = winsorize(data, lower_percentile=25, upper_percentile=75)
    assert res.clipped_low == 0 and res.clipped_high == 0
    assert res.clipped == (10.0, 10.0, 10.0, 10.0)


def test_zero_and_hundred_percentiles_clip_nothing():
    data = [1, 2, 3, 4, 5]
    res = winsorize(data, lower_percentile=0, upper_percentile=100)
    assert res.clipped_low == 0 and res.clipped_high == 0
    assert res.clipped == (1.0, 2.0, 3.0, 4.0, 5.0)


def test_single_value_series():
    res = winsorize([42], lower_percentile=5, upper_percentile=95)
    assert res.clipped == (42.0,)
    assert res.clipped_low == 0 and res.clipped_high == 0


def test_all_identical_values():
    res = winsorize([7, 7, 7], lower_percentile=10, upper_percentile=90)
    assert res.clipped == (7.0, 7.0, 7.0)
    assert res.lower_bound == 7.0 and res.upper_bound == 7.0


def test_rounding_of_bounds():
    data = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    res = winsorize(data, lower_percentile=5, upper_percentile=95, digits=2)
    assert res.lower_bound == round(res.lower_bound, 2)


# --- validation ------------------------------------------------------------


def test_empty_values_rejected():
    with pytest.raises(ValueError):
        winsorize([])


def test_lower_above_upper_rejected():
    with pytest.raises(ValueError):
        winsorize([1, 2, 3], lower_percentile=90, upper_percentile=10)


def test_percentile_out_of_range_rejected():
    with pytest.raises(ValueError):
        winsorize([1, 2, 3], lower_percentile=-5)


def test_boolean_value_rejected():
    with pytest.raises(TypeError):
        winsorize([True, 1, 2])


def test_non_finite_value_rejected():
    with pytest.raises(ValueError):
        winsorize([1, 2, float("inf")])


def test_digits_must_be_non_negative():
    with pytest.raises(ValueError):
        winsorize([1, 2, 3], digits=-1)


def test_percentile_must_be_numeric():
    with pytest.raises(TypeError):
        winsorize([1, 2, 3], lower_percentile="5")
