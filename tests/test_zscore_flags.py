import pytest

from reporting_core.zscore_flags import (
    Flag,
    Sample,
    modified_zscore_flags,
    zscore_flags,
)


def series(values, *, start=1):
    return [Sample(f"P{start + i:02d}", float(v)) for i, v in enumerate(values)]


# --- zscore_flags: core behaviour ------------------------------------------


def test_flags_extreme_high_point():
    # a cluster around 10 plus one huge spike
    data = series([10, 10, 11, 9, 10, 100])
    flags = zscore_flags(data, threshold=2.0)
    spike = flags[-1]
    assert spike.is_outlier is True
    assert spike.direction == "high"


def test_flags_extreme_low_point():
    data = series([100, 100, 99, 101, 100, 1])
    flags = zscore_flags(data, threshold=2.0)
    assert flags[-1].is_outlier is True
    assert flags[-1].direction == "low"


def test_no_outliers_under_high_threshold():
    flags = zscore_flags(series([10, 11, 9, 10, 12, 8]), threshold=3.0)
    assert all(not f.is_outlier for f in flags)
    assert all(f.direction is None for f in flags)


def test_scores_are_symmetric_mean_zero():
    flags = zscore_flags(series([1, 2, 3, 4, 5]))
    # z-scores sum to ~0 for any series (mean-centred)
    assert round(sum(f.score for f in flags), 6) == 0.0


def test_result_length_and_order_preserved():
    pts = series([1, 5, 2, 8])
    flags = zscore_flags(pts)
    assert len(flags) == len(pts)
    assert [f.label for f in flags] == [p.label for p in pts]
    assert all(isinstance(f, Flag) for f in flags)


def test_zero_spread_gives_zero_scores():
    flags = zscore_flags(series([5, 5, 5, 5]))
    assert all(f.score == 0.0 for f in flags)
    assert all(not f.is_outlier for f in flags)


def test_single_point_not_outlier():
    flags = zscore_flags(series([42]))
    assert flags[0].score == 0.0 and flags[0].is_outlier is False


def test_empty_series_returns_empty():
    assert zscore_flags([]) == ()


# --- modified_zscore_flags -------------------------------------------------


def test_modified_flags_robust_to_masking():
    # two large spikes would inflate a plain stdev and hide themselves; the
    # MAD-based score still catches them (the cluster has real spread so the
    # MAD is non-zero, but the median stays inside the cluster).
    data = series([10, 11, 12, 13, 14, 15, 16, 500, 510])
    flags = modified_zscore_flags(data, threshold=3.5)
    flagged = [f for f in flags if f.is_outlier]
    assert len(flagged) == 2
    assert all(f.direction == "high" for f in flagged)


def test_modified_zero_mad_gives_zero_scores():
    # majority identical -> MAD is 0 -> no robust spread -> nothing flagged
    flags = modified_zscore_flags(series([7, 7, 7, 7, 7, 20]))
    assert all(f.score == 0.0 for f in flags)
    assert all(not f.is_outlier for f in flags)


def test_modified_empty_series():
    assert modified_zscore_flags([]) == ()


def test_modified_single_point():
    flags = modified_zscore_flags(series([99]))
    assert flags[0].score == 0.0 and flags[0].is_outlier is False


# --- validation (shared) ---------------------------------------------------


def test_rejects_non_sample():
    with pytest.raises(TypeError):
        zscore_flags([(1, 2.0)])


def test_rejects_duplicate_labels():
    with pytest.raises(ValueError):
        zscore_flags([Sample("P01", 1.0), Sample("P01", 2.0)])


def test_rejects_empty_label():
    with pytest.raises(ValueError):
        modified_zscore_flags([Sample("  ", 1.0)])


def test_rejects_boolean_value():
    with pytest.raises(TypeError):
        zscore_flags([Sample("P01", True)])


def test_rejects_non_finite_value():
    with pytest.raises(ValueError):
        zscore_flags([Sample("P01", float("nan"))])


def test_threshold_must_be_positive():
    with pytest.raises(ValueError):
        zscore_flags(series([1, 2, 3]), threshold=0)


def test_threshold_must_be_numeric():
    with pytest.raises(TypeError):
        modified_zscore_flags(series([1, 2, 3]), threshold="3")


def test_digits_must_be_non_negative():
    with pytest.raises(ValueError):
        zscore_flags(series([1, 2, 3]), digits=-1)
