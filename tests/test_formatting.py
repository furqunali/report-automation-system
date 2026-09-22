import math

import pytest

from reporting_core.formatting import (
    format_currency,
    format_number,
    format_percent,
)

# --- format_number ---------------------------------------------------------


def test_format_number_default_grouping_and_decimals():
    assert format_number(1234.5) == "1,234.50"
    assert format_number(1000000) == "1,000,000.00"


def test_format_number_without_thousands():
    assert format_number(1234.5, thousands=False) == "1234.50"


def test_format_number_custom_decimals_rounds_half_even_bankers():
    # Python's format() uses round-half-to-even; assert the actual behavior.
    assert format_number(1234.567, decimals=0) == "1,235"
    assert format_number(2.5, decimals=0) == "2"
    assert format_number(3.5, decimals=0) == "4"


def test_format_number_zero_decimals_has_no_point():
    assert "." not in format_number(1234, decimals=0)


def test_format_number_negative():
    assert format_number(-1234.5) == "-1,234.50"


def test_format_number_normalizes_negative_zero():
    assert format_number(-0.0) == "0.00"
    assert format_number(-0.001, decimals=2) == "0.00"
    # A value that does NOT round to zero keeps its sign.
    assert format_number(-0.005, decimals=2) == "-0.01"


def test_format_number_rejects_bool():
    with pytest.raises(TypeError):
        format_number(True)


def test_format_number_rejects_non_number():
    with pytest.raises(TypeError):
        format_number("100")


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_format_number_rejects_non_finite(bad):
    with pytest.raises(ValueError):
        format_number(bad)


def test_format_number_rejects_negative_decimals():
    with pytest.raises(ValueError):
        format_number(1.0, decimals=-1)


def test_format_number_rejects_bool_decimals():
    with pytest.raises(TypeError):
        format_number(1.0, decimals=True)


# --- format_currency -------------------------------------------------------


def test_format_currency_default_symbol():
    assert format_currency(1234.5) == "$1,234.50"


def test_format_currency_custom_symbol_and_decimals():
    assert format_currency(1000, symbol="€", decimals=0) == "€1,000"


def test_format_currency_empty_symbol():
    assert format_currency(50) == "$50.00"
    assert format_currency(50, symbol="") == "50.00"


def test_format_currency_negative_default_sign_before_symbol():
    assert format_currency(-1234.5) == "-$1,234.50"


def test_format_currency_negative_accounting_parentheses():
    assert format_currency(-1234.5, accounting=True) == "($1,234.50)"


def test_format_currency_positive_unaffected_by_accounting():
    assert format_currency(1234.5, accounting=True) == "$1,234.50"


def test_format_currency_normalizes_negative_zero():
    assert format_currency(-0.0) == "$0.00"
    assert format_currency(-0.001, accounting=True) == "$0.00"


def test_format_currency_rejects_non_string_symbol():
    with pytest.raises(TypeError):
        format_currency(1.0, symbol=1)


def test_format_currency_rejects_non_finite():
    with pytest.raises(ValueError):
        format_currency(math.inf)


# --- format_percent --------------------------------------------------------


def test_format_percent_default_treats_value_as_percentage():
    assert format_percent(25) == "25.0%"
    assert format_percent(3.456, decimals=2) == "3.46%"


def test_format_percent_as_ratio_scales_by_100():
    assert format_percent(0.25, as_ratio=True) == "25.0%"
    assert format_percent(1, as_ratio=True) == "100.0%"


def test_format_percent_signed_adds_plus_for_positive_only():
    assert format_percent(3.5, signed=True) == "+3.5%"
    assert format_percent(-3.5, signed=True) == "-3.5%"
    assert format_percent(0, signed=True) == "0.0%"


def test_format_percent_no_thousands_grouping():
    # Percentages should not be comma-grouped even when large.
    assert format_percent(1234.5) == "1234.5%"


def test_format_percent_normalizes_negative_zero():
    assert format_percent(-0.0001, decimals=1) == "0.0%"


def test_format_percent_rejects_non_finite():
    with pytest.raises(ValueError):
        format_percent(math.nan)


def test_format_percent_rejects_negative_decimals():
    with pytest.raises(ValueError):
        format_percent(1.0, decimals=-2)
