import pytest

from reporting_core.weighted_average import (
    Row,
    weighted_mean,
    weighted_percentage,
    weighted_share,
)


def rows(pairs):
    return [Row(float(v), float(w)) for v, w in pairs]


# --- weighted_mean: core behaviour -----------------------------------------


def test_weighted_mean_basic():
    # values 10 and 20 with weights 1 and 3 -> (10 + 60)/4 = 17.5
    assert weighted_mean(rows([(10, 1), (20, 3)])) == 17.5


def test_equal_weights_equal_plain_mean():
    assert weighted_mean(rows([(2, 5), (4, 5), (6, 5)])) == 4.0


def test_single_row_is_its_own_value():
    assert weighted_mean(rows([(42, 7)])) == 42.0


def test_zero_weight_row_is_ignored():
    # the zero-weight row must not affect the blend
    assert weighted_mean(rows([(100, 0), (10, 1)])) == 10.0


def test_negative_values_supported():
    assert weighted_mean(rows([(-10, 1), (10, 1)])) == 0.0


def test_rounding_applied():
    # (1*1 + 2*1)/2 forced to thirds: values 1,1,2 weights 1,1,1 -> 1.3333
    assert weighted_mean(rows([(1, 1), (1, 1), (2, 1)]), digits=4) == 1.3333


# --- weighted_percentage ---------------------------------------------------


def test_weighted_percentage_from_fractions():
    # margins 0.20 and 0.40 weighted by 1 and 3 -> 0.35 -> 35.0%
    assert weighted_percentage(rows([(0.20, 1), (0.40, 3)])) == 35.0


def test_weighted_percentage_already_percent():
    assert weighted_percentage(rows([(20, 1), (40, 3)]), as_fraction=False) == 35.0


def test_weighted_percentage_rejects_non_bool_as_fraction():
    with pytest.raises(TypeError):
        weighted_percentage(rows([(0.1, 1)]), as_fraction=1)


# --- weighted_share --------------------------------------------------------


def test_weighted_share_sums_to_one():
    shares = weighted_share(rows([(0, 1), (0, 3)]))
    assert shares == (0.25, 0.75)
    assert round(sum(shares), 6) == 1.0


def test_weighted_share_zero_weight_is_zero():
    shares = weighted_share(rows([(5, 0), (5, 2)]))
    assert shares == (0.0, 1.0)


def test_weighted_share_order_preserved():
    shares = weighted_share(rows([(1, 2), (1, 2), (1, 4)]))
    assert shares == (0.25, 0.25, 0.5)


# --- validation ------------------------------------------------------------


def test_empty_rows_rejected():
    with pytest.raises(ValueError):
        weighted_mean([])


def test_all_zero_weights_rejected():
    with pytest.raises(ValueError):
        weighted_mean(rows([(10, 0), (20, 0)]))


def test_negative_weight_rejected():
    with pytest.raises(ValueError):
        weighted_mean(rows([(10, -1), (20, 2)]))


def test_non_row_rejected():
    with pytest.raises(TypeError):
        weighted_mean([(10, 1)])


def test_boolean_value_rejected():
    with pytest.raises(TypeError):
        weighted_mean([Row(True, 1.0)])


def test_boolean_weight_rejected():
    with pytest.raises(TypeError):
        weighted_mean([Row(1.0, True)])


def test_non_finite_value_rejected():
    with pytest.raises(ValueError):
        weighted_mean([Row(float("inf"), 1.0)])


def test_non_finite_weight_rejected():
    with pytest.raises(ValueError):
        weighted_mean([Row(1.0, float("nan"))])


def test_digits_must_be_non_negative():
    with pytest.raises(ValueError):
        weighted_mean(rows([(1, 1)]), digits=-1)


def test_digits_must_be_int_not_bool():
    with pytest.raises(TypeError):
        weighted_mean(rows([(1, 1)]), digits=True)
