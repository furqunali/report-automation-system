"""Human-readable number, currency, and percent formatting.

Across the package numbers are formatted ad hoc at each render site
(:mod:`reporting_core.markdown_report`, the dashboard, the CLI), each with its
own ``"{:,.2f}"``-style literal.  This module centralizes that concern into a
small, well-validated set of helpers so every surface renders figures the same
way: thousands separators, a fixed number of decimals, a normalized zero (never
a misleading ``-0.00``), and explicit, fail-fast handling of the values that
have no sensible display - ``NaN``, infinities, booleans, and non-numbers.

The helpers are pure and deterministic: the same input always yields the same
string, so the output is safe to diff in tests and in review.
"""
from __future__ import annotations

import math
from numbers import Real

__all__ = ["format_currency", "format_number", "format_percent"]


def _coerce(value: object) -> float:
    """Validate ``value`` is a real, finite number and return it as ``float``.

    ``bool`` is rejected even though it is a subclass of ``int`` - formatting
    ``True`` as ``1.00`` is almost always a bug at the call site.  ``NaN`` and
    the infinities are rejected because they have no meaningful fixed-decimal
    rendering and would silently corrupt a report.
    """
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError("value must be a real number")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("value must be finite (not NaN or infinity)")
    return number


def _check_decimals(decimals: int) -> None:
    if isinstance(decimals, bool) or not isinstance(decimals, int):
        raise TypeError("decimals must be an integer")
    if decimals < 0:
        raise ValueError("decimals must be non-negative")


def _normalize_zero(number: float, decimals: int) -> float:
    """Collapse a value that rounds to zero onto positive ``0.0``.

    This prevents a small negative figure (or literal ``-0.0``) from rendering
    as ``-0.00``, which reads as a real, if tiny, loss.
    """
    if round(number, decimals) == 0:
        return 0.0
    return number


def format_number(
    value: object,
    *,
    decimals: int = 2,
    thousands: bool = True,
) -> str:
    """Format a real number with fixed decimals and optional grouping.

    Parameters
    ----------
    value:
        Any real, finite number.  Booleans, ``NaN``, and infinities are
        rejected rather than silently coerced.
    decimals:
        Number of digits after the decimal point (non-negative). ``0`` yields a
        whole-number string with no decimal point.
    thousands:
        When ``True`` (the default) digits are grouped with commas
        (``1,234.50``); when ``False`` the grouping is omitted (``1234.50``).

    Examples
    --------
    >>> format_number(1234.5)
    '1,234.50'
    >>> format_number(-0.001, decimals=2)
    '0.00'
    >>> format_number(1234.567, decimals=0)
    '1,235'
    """
    _check_decimals(decimals)
    number = _normalize_zero(_coerce(value), decimals)
    spec = f",.{decimals}f" if thousands else f".{decimals}f"
    return format(number, spec)


def format_currency(
    value: object,
    *,
    symbol: str = "$",
    decimals: int = 2,
    thousands: bool = True,
    accounting: bool = False,
) -> str:
    """Format a monetary amount with a currency symbol.

    Parameters
    ----------
    symbol:
        The currency symbol prefixed to the amount (e.g. ``"$"``, ``"£"``,
        ``"€"``).  May be empty.
    decimals, thousands:
        As in :func:`format_number`.
    accounting:
        When ``True`` a negative amount is wrapped in parentheses with no minus
        sign (``($1,234.56)``), the convention in financial statements.  When
        ``False`` (the default) the minus precedes the symbol (``-$1,234.56``).

    Examples
    --------
    >>> format_currency(1234.5)
    '$1,234.50'
    >>> format_currency(-1234.5, accounting=True)
    '($1,234.50)'
    >>> format_currency(1000, symbol="€", decimals=0)
    '€1,000'
    """
    if not isinstance(symbol, str):
        raise TypeError("symbol must be a string")
    number = _normalize_zero(_coerce(value), decimals)
    magnitude = format_number(abs(number), decimals=decimals, thousands=thousands)
    if number < 0:
        if accounting:
            return f"({symbol}{magnitude})"
        return f"-{symbol}{magnitude}"
    return f"{symbol}{magnitude}"


def format_percent(
    value: object,
    *,
    decimals: int = 1,
    signed: bool = False,
    as_ratio: bool = False,
) -> str:
    """Format a value as a percentage string ending in ``%``.

    Parameters
    ----------
    value:
        By default this is treated as an already-scaled percentage, so ``25``
        renders as ``25.0%``.  Set ``as_ratio=True`` to pass a 0-1 ratio
        instead, so ``0.25`` renders as ``25.0%``.
    decimals:
        Number of digits after the decimal point (non-negative).
    signed:
        When ``True`` a leading ``+`` is added to positive values (``+3.5%``),
        useful for variance and change figures.  Zero is never signed.
    as_ratio:
        When ``True`` the input is multiplied by 100 before formatting.

    Examples
    --------
    >>> format_percent(25)
    '25.0%'
    >>> format_percent(0.25, as_ratio=True)
    '25.0%'
    >>> format_percent(3.5, signed=True)
    '+3.5%'
    """
    _check_decimals(decimals)
    number = _coerce(value)
    if as_ratio:
        number *= 100
    number = _normalize_zero(number, decimals)
    sign = "+" if signed and number > 0 else ""
    return f"{sign}{format_number(number, decimals=decimals, thousands=False)}%"
