import pytest

from reporting_core.bucketize import (
    Bucket,
    fixed_width_buckets,
    quantile,
    quantile_buckets,
)


# --- fixed_width_buckets: core behaviour -----------------------------------


def test_fixed_width_count_and_coverage():
    data = list(range(0, 100))  # 0..99
    buckets = fixed_width_buckets(data, bins=10)
    assert len(buckets) == 10
    assert sum(b.count for b in buckets) == len(data)
    assert all(isinstance(b, Bucket) for b in buckets)


def test_fixed_width_equal_ranges():
    buckets = fixed_width_buckets([0, 10], bins=2)
    assert buckets[0].lower == 0.0 and buckets[0].upper == 5.0
    assert buckets[1].lower == 5.0 and buckets[1].upper == 10.0


def test_fixed_width_max_lands_in_last_bucket():
    data = [0, 1, 2, 3, 4, 5, 6, 7, 8, 10]
    buckets = fixed_width_buckets(data, bins=5)
    # the maximum (10) must be captured by the closed final bucket
    assert buckets[-1].count >= 1
    assert sum(b.count for b in buckets) == len(data)


def test_fixed_width_single_bin():
    buckets = fixed_width_buckets([1, 2, 3, 4], bins=1)
    assert len(buckets) == 1
    assert buckets[0].count == 4


def test_fixed_width_all_identical_collapses_to_one():
    buckets = fixed_width_buckets([5, 5, 5], bins=4)
    assert len(buckets) == 1
    assert buckets[0].lower == 5.0 and buckets[0].upper == 5.0
    assert buckets[0].count == 3


def test_fixed_width_label_format():
    buckets = fixed_width_buckets([0, 10], bins=2, digits=1)
    assert buckets[0].label == "[0.0, 5.0)"
    assert buckets[-1].label.endswith("]")  # final bucket closed


# --- quantile helper -------------------------------------------------------


def test_quantile_bounds():
    data = [1, 2, 3, 4, 5]
    assert quantile(data, 0.0) == 1.0
    assert quantile(data, 1.0) == 5.0
    assert quantile(data, 0.5) == 3.0


def test_quantile_rejects_out_of_range():
    with pytest.raises(ValueError):
        quantile([1, 2, 3], 1.5)


# --- quantile_buckets ------------------------------------------------------


def test_quantile_buckets_roughly_equal_counts():
    data = list(range(1, 101))  # 1..100
    buckets = quantile_buckets(data, bins=4)
    assert sum(b.count for b in buckets) == len(data)
    # each quartile should hold about a quarter of the points
    assert all(20 <= b.count <= 30 for b in buckets)


def test_quantile_buckets_skewed_data():
    # heavily skewed: quantile bins adapt where fixed-width would not
    data = [1, 1, 1, 1, 2, 3, 100]
    buckets = quantile_buckets(data, bins=4)
    assert sum(b.count for b in buckets) == len(data)


def test_quantile_buckets_low_cardinality_merges_edges():
    # repeated values collapse edges -> fewer than `bins` buckets, no empties
    data = [1, 1, 1, 1, 2, 2, 2, 2]
    buckets = quantile_buckets(data, bins=4)
    assert sum(b.count for b in buckets) == len(data)
    assert all(b.count > 0 for b in buckets)
    assert len(buckets) <= 4


def test_quantile_buckets_all_identical():
    buckets = quantile_buckets([9, 9, 9], bins=3)
    assert len(buckets) == 1
    assert buckets[0].count == 3


def test_quantile_buckets_single_value():
    buckets = quantile_buckets([42], bins=4)
    assert len(buckets) == 1
    assert buckets[0].count == 1


# --- validation (shared) ---------------------------------------------------


def test_empty_values_rejected_fixed():
    with pytest.raises(ValueError):
        fixed_width_buckets([])


def test_empty_values_rejected_quantile():
    with pytest.raises(ValueError):
        quantile_buckets([])


def test_bins_must_be_positive():
    with pytest.raises(ValueError):
        fixed_width_buckets([1, 2, 3], bins=0)


def test_bins_must_be_int_not_bool():
    with pytest.raises(TypeError):
        quantile_buckets([1, 2, 3], bins=True)


def test_boolean_value_rejected():
    with pytest.raises(TypeError):
        fixed_width_buckets([True, 1, 2])


def test_non_finite_value_rejected():
    with pytest.raises(ValueError):
        quantile_buckets([1, 2, float("inf")])


def test_digits_must_be_non_negative():
    with pytest.raises(ValueError):
        fixed_width_buckets([1, 2, 3], digits=-1)
