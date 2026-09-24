"""Running totals, running share-of-total, and running max/min over a series.

Reports frequently want the *accumulating* view of a series rather than just
the per-period numbers: year-to-date sales after each month, what fraction of
the annual total each cumulative point represents, and the best/worst reading
seen so far as the year unfolds.  These are all single-pass running statistics
over a time-ordered series.

Given a list of :class:`Point` (a label plus a finite value) this module
produces one :class:`Running` per period, carrying:

* ``cumulative`` - the running total up to and including this period,
* ``running_share`` - that running total as a percentage of the grand total of
  the whole series (``None`` when the grand total is zero, so no divide-by-zero),
* ``running_max`` / ``running_min`` - the largest / smallest single value seen
  up to and including this period.

The series is walked strictly left-to-right; nothing is reordered and no future
period ever influences an earlier one.  Everything is deterministic and rounded
on output.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real


@dataclass(frozen=True)
class Point:
    """One observation: a non-empty ``label`` and a finite ``value``."""

    label: str
    value: float


@dataclass(frozen=True)
class Running:
    """The running-statistics view of a single period.

    ``cumulative`` is the running total through this period; ``running_share``
    is that total over the series grand total, as a percentage, or ``None`` when
    the grand total is zero.  ``running_max`` / ``running_min`` are the extreme
    single values seen so far.
    """

    label: str
    value: float
    cumulative: float
    running_share: float | None
    running_max: float
    running_min: float


def _validate_digits(digits: int) -> int:
    if not isinstance(digits, int) or isinstance(digits, bool):
        raise TypeError("digits must be an integer")
    if digits < 0:
        raise ValueError("digits must be non-negative")
    return digits


def _validate_series(series: list[Point]) -> list[Point]:
    points = list(series)
    seen: set[str] = set()
    for point in points:
        if not isinstance(point, Point):
            raise TypeError("series must contain Point instances")
        if not isinstance(point.label, str) or not point.label.strip():
            raise ValueError("each Point.label must be a non-empty string")
        if point.label in seen:
            raise ValueError(f"duplicate label in series: {point.label!r}")
        seen.add(point.label)
        if not isinstance(point.value, Real) or isinstance(point.value, bool):
            raise TypeError("each Point.value must be numeric")
        if not math.isfinite(float(point.value)):
            raise ValueError("each Point.value must be finite")
    return points


def running_stats(series: list[Point], *, digits: int = 2) -> tuple[Running, ...]:
    """Compute running total, share, and max/min over a time-ordered series.

    Parameters
    ----------
    series:
        The observations, already in chronological order.  May be empty (the
        result is then an empty tuple).  Labels must be unique.
    digits:
        Decimal places for the numeric fields.  Must be non-negative.

    Returns
    -------
    tuple[Running, ...]
        One :class:`Running` per input point, in order.  ``running_share`` is
        ``None`` for every point when the series grand total is zero (there is
        no meaningful denominator); otherwise it is the running total as a
        percentage of that grand total.  Note that with mixed-sign values a
        running share can exceed 100% or go negative - that is faithful, not a
        bug.
    """
    digits = _validate_digits(digits)
    points = _validate_series(series)

    grand_total = math.fsum(float(p.value) for p in points)
    share_defined = grand_total != 0

    results: list[Running] = []
    total = 0.0
    current_max: float | None = None
    current_min: float | None = None
    for point in points:
        val = float(point.value)
        total += val
        current_max = val if current_max is None else max(current_max, val)
        current_min = val if current_min is None else min(current_min, val)
        share = round(total / grand_total * 100.0, digits) if share_defined else None
        results.append(
            Running(
                label=point.label,
                value=round(val, digits),
                cumulative=round(total, digits),
                running_share=share,
                running_max=round(current_max, digits),
                running_min=round(current_min, digits),
            )
        )
    return tuple(results)


def running_total(series: list[Point], *, digits: int = 2) -> tuple[float, ...]:
    """Just the running (cumulative) totals, one per period, in order.

    A convenience projection of :func:`running_stats` for callers that only
    need the year-to-date column and nothing else.
    """
    return tuple(r.cumulative for r in running_stats(series, digits=digits))
