"""Weighted mean and weighted percentage across value+weight rows.

A plain average treats every row the same, which is wrong for most report
roll-ups: a blended margin across four stores should count the big store more
than the tiny one, an average price should be weighted by units sold, a group
attainment should be weighted by target size.  The right tool is a weighted
mean, ``sum(value * weight) / sum(weight)``.

This module works over a list of :class:`Row` (a value paired with a
non-negative weight) and offers:

* :func:`weighted_mean` - the weighted average of the values,
* :func:`weighted_percentage` - a weighted average expressed as a percentage,
  for blending rates/ratios that are already fractions or already percentages,
* :func:`weighted_share` - each row's fraction of the total weight, so a caller
  can show "how much did each row drive the blend".

Weights are validated to be finite and non-negative, and the total weight must
be strictly positive - an all-zero weighting has no defined mean, and this
module refuses to invent one rather than dividing by zero.  Everything is
deterministic and rounded on output.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real


@dataclass(frozen=True)
class Row:
    """One weighted observation: a finite ``value`` and its ``weight``.

    ``weight`` must be finite and ``>= 0``.  A zero weight is allowed (the row
    simply contributes nothing to the blend) as long as *some* row carries
    positive weight, so a caller can pass a full table and let genuinely empty
    rows fall out naturally.
    """

    value: float
    weight: float


def _validate_digits(digits: int) -> int:
    if not isinstance(digits, int) or isinstance(digits, bool):
        raise TypeError("digits must be an integer")
    if digits < 0:
        raise ValueError("digits must be non-negative")
    return digits


def _validate_rows(rows: list[Row]) -> list[Row]:
    items = list(rows)
    if not items:
        raise ValueError("rows must not be empty")
    for row in items:
        if not isinstance(row, Row):
            raise TypeError("rows must contain Row instances")
        if not isinstance(row.value, Real) or isinstance(row.value, bool):
            raise TypeError("each Row.value must be numeric")
        if not math.isfinite(float(row.value)):
            raise ValueError("each Row.value must be finite")
        if not isinstance(row.weight, Real) or isinstance(row.weight, bool):
            raise TypeError("each Row.weight must be numeric")
        if not math.isfinite(float(row.weight)):
            raise ValueError("each Row.weight must be finite")
        if float(row.weight) < 0:
            raise ValueError("each Row.weight must be non-negative")
    return items


def _total_weight(rows: list[Row]) -> float:
    total = math.fsum(float(row.weight) for row in rows)
    if total <= 0:
        raise ValueError("total weight must be positive (weights are all zero)")
    return total


def weighted_mean(rows: list[Row], *, digits: int = 4) -> float:
    """Weighted arithmetic mean of the row values.

    Computes ``sum(value * weight) / sum(weight)`` using :func:`math.fsum` for
    numerically stable accumulation, then rounds to ``digits`` places.

    Parameters
    ----------
    rows:
        A non-empty list of :class:`Row`.  Weights must be finite and
        non-negative, and their total must be strictly positive.
    digits:
        Decimal places for the result.  Must be non-negative.

    Returns
    -------
    float
        The weighted mean.  Rows with zero weight contribute nothing.
    """
    digits = _validate_digits(digits)
    items = _validate_rows(rows)
    total = _total_weight(items)
    numerator = math.fsum(float(row.value) * float(row.weight) for row in items)
    return round(numerator / total, digits)


def weighted_percentage(rows: list[Row], *, digits: int = 2, as_fraction: bool = True) -> float:
    """Weighted average of rates, returned as a percentage.

    Use this to blend per-row ratios - margins, attainment, defect rates - into
    a single headline percentage weighted by row size.  When ``as_fraction`` is
    ``True`` (the default) each ``value`` is treated as a fraction in the
    ``0..1`` sense (``0.25`` -> ``25%``) and the weighted mean is scaled by
    ``100``.  When ``False`` the values are already percentages (``25`` ->
    ``25%``) and are blended as-is.

    Parameters
    ----------
    rows:
        A non-empty list of :class:`Row`; the same weight rules as
        :func:`weighted_mean` apply.
    digits:
        Decimal places for the resulting percentage.
    as_fraction:
        Whether ``value`` is a ``0..1`` fraction (scale by 100) or already a
        percentage (blend directly).

    Returns
    -------
    float
        The weighted percentage.
    """
    digits = _validate_digits(digits)
    if not isinstance(as_fraction, bool):
        raise TypeError("as_fraction must be a bool")
    mean = weighted_mean(rows, digits=digits + 6)
    scaled = mean * 100.0 if as_fraction else mean
    return round(scaled, digits)


def weighted_share(rows: list[Row], *, digits: int = 4) -> tuple[float, ...]:
    """Each row's share of the total weight, as a fraction in ``0..1``.

    Returns one number per row: ``weight / sum(weight)``.  This is the exact
    influence each row exerts on :func:`weighted_mean`, so a report can show
    which rows are actually driving a blended figure.  Zero-weight rows get a
    share of ``0.0``.

    Parameters
    ----------
    rows:
        A non-empty list of :class:`Row`; the same weight rules apply.
    digits:
        Decimal places for each share.

    Returns
    -------
    tuple[float, ...]
        The per-row shares, in input order.  They sum to ``1.0`` up to rounding.
    """
    digits = _validate_digits(digits)
    items = _validate_rows(rows)
    total = _total_weight(items)
    return tuple(round(float(row.weight) / total, digits) for row in items)
