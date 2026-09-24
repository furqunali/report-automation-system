"""Winsorize a numeric series - clip extremes to percentile bounds.

A handful of wild readings - a mis-keyed order ten times too large, a negative
price from a bad export - can drag an average or a total wildly off. Dropping
them loses information and changes the row count; winsorizing instead *clips*
them to a chosen percentile bound, so the aggregate stops being hostage to the
tails while every observation still counts.

This module computes the lower and upper percentile thresholds of a series and
returns a :class:`WinsorizeResult`:

* ``clipped`` - the series with every value pulled to within
  ``[lower_bound, upper_bound]`` (order preserved, length unchanged),
* ``lower_bound`` / ``upper_bound`` - the thresholds actually applied,
* ``clipped_low`` / ``clipped_high`` - how many values were pulled up from
  below and down from above, so a report can disclose exactly how much was
  clamped.

Percentiles use linear interpolation between order statistics (the common
"type 7" definition), so the bounds are stable and match what most analysts
expect. Everything is deterministic and validated up front.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real


@dataclass(frozen=True)
class WinsorizeResult:
    """The outcome of winsorizing a series.

    ``clipped`` has the same length and order as the input.  ``clipped_low`` and
    ``clipped_high`` count how many values sat strictly below ``lower_bound`` or
    strictly above ``upper_bound`` respectively and were therefore moved.
    """

    clipped: tuple[float, ...]
    lower_bound: float
    upper_bound: float
    clipped_low: int
    clipped_high: int


def _validate_digits(digits: int) -> int:
    if not isinstance(digits, int) or isinstance(digits, bool):
        raise TypeError("digits must be an integer")
    if digits < 0:
        raise ValueError("digits must be non-negative")
    return digits


def _validate_percentile(name: str, value: float) -> float:
    if not isinstance(value, Real) or isinstance(value, bool):
        raise TypeError(f"{name} must be numeric")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    if not 0.0 <= value <= 100.0:
        raise ValueError(f"{name} must be between 0 and 100 inclusive")
    return value


def _validate_values(values: list[float]) -> list[float]:
    items = list(values)
    if not items:
        raise ValueError("values must not be empty")
    out: list[float] = []
    for v in items:
        if not isinstance(v, Real) or isinstance(v, bool):
            raise TypeError("each value must be numeric")
        v = float(v)
        if not math.isfinite(v):
            raise ValueError("each value must be finite")
        out.append(v)
    return out


def percentile(values: list[float], q: float) -> float:
    """The ``q``-th percentile of ``values`` by linear interpolation (type 7).

    ``q`` is in ``[0, 100]``.  For ``q=0`` this is the minimum and for ``q=100``
    the maximum; in between it interpolates linearly between the two nearest
    order statistics - the same definition used by ``numpy.percentile`` with its
    default method, so results line up with common analyst tooling.
    """
    q = _validate_percentile("q", q)
    data = sorted(_validate_values(values))
    if len(data) == 1:
        return data[0]
    rank = q / 100.0 * (len(data) - 1)
    low = math.floor(rank)
    high = math.ceil(rank)
    if low == high:
        return data[low]
    frac = rank - low
    return data[low] + (data[high] - data[low]) * frac


def winsorize(
    values: list[float],
    *,
    lower_percentile: float = 5.0,
    upper_percentile: float = 95.0,
    digits: int = 4,
) -> WinsorizeResult:
    """Clip a series to its lower/upper percentile bounds.

    Parameters
    ----------
    values:
        A non-empty list of finite numbers.  Order is preserved in the output.
    lower_percentile:
        The percentile defining the floor (values below it are raised to it).
        In ``[0, 100]`` and must be ``<= upper_percentile``.  ``0`` disables
        the lower clip (the floor becomes the minimum, which changes nothing).
    upper_percentile:
        The percentile defining the ceiling (values above it are lowered to
        it).  In ``[0, 100]`` and must be ``>= lower_percentile``.
    digits:
        Decimal places for the clipped values and the reported bounds.

    Returns
    -------
    WinsorizeResult
        The clipped series plus the bounds applied and the count moved at each
        end.  A value sitting exactly on a bound is left untouched and not
        counted as clipped.
    """
    digits = _validate_digits(digits)
    lower_percentile = _validate_percentile("lower_percentile", lower_percentile)
    upper_percentile = _validate_percentile("upper_percentile", upper_percentile)
    if lower_percentile > upper_percentile:
        raise ValueError("lower_percentile must not exceed upper_percentile")
    data = _validate_values(values)

    lower_bound = percentile(data, lower_percentile)
    upper_bound = percentile(data, upper_percentile)

    clipped: list[float] = []
    clipped_low = 0
    clipped_high = 0
    for v in data:
        if v < lower_bound:
            clipped_low += 1
            clipped.append(round(lower_bound, digits))
        elif v > upper_bound:
            clipped_high += 1
            clipped.append(round(upper_bound, digits))
        else:
            clipped.append(round(v, digits))
    return WinsorizeResult(
        clipped=tuple(clipped),
        lower_bound=round(lower_bound, digits),
        upper_bound=round(upper_bound, digits),
        clipped_low=clipped_low,
        clipped_high=clipped_high,
    )
