"""Period-over-period and prior-year growth percentages for a time series.

Every monthly management report eventually asks the same two questions of a
headline number: "how does this period compare to the one just before it?"
(sequential, period-over-period growth) and "how does it compare to the same
period a year ago?" (prior-year, year-over-year growth).  Both are simple
percentage changes, but both are riddled with the same trap - a zero or
missing baseline - which naively computed either divides by zero or prints a
meaningless ``inf``.

This module turns a time-ordered series of :class:`Period` values into a
:class:`Growth` per period, each carrying:

* the raw ``value`` at that period,
* the ``prev_value`` one step back and the period-over-period ``pop_pct``,
* the ``prior_year_value`` ``periods_per_year`` steps back and the
  year-over-year ``yoy_pct``.

Any growth percentage whose baseline is ``None``, missing (not enough history
yet), or exactly zero is reported as ``None`` - never a divide-by-zero, never a
fabricated infinity.  A caller can always tell "no comparison available" apart
from a genuine "0.0% flat".

The series is assumed to already be in chronological order; this module never
reorders it.  Everything is deterministic and validated up front, so the same
series always yields the same output.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real


@dataclass(frozen=True)
class Period:
    """One observation in a time-ordered series.

    ``label`` is a human-readable period tag (e.g. ``"2026-08"``) and must be a
    non-empty string.  ``value`` may be a finite number or ``None`` - ``None``
    models a period with no reading at all (a gap), which then acts as an
    unusable baseline for any period that compares against it.
    """

    label: str
    value: float | None


@dataclass(frozen=True)
class Growth:
    """The growth view of a single period.

    ``pop_pct`` is the period-over-period percentage change from ``prev_value``;
    ``yoy_pct`` is the change from ``prior_year_value`` (the observation
    ``periods_per_year`` steps earlier).  Either percentage is ``None`` whenever
    its baseline is missing, ``None``, or zero.
    """

    label: str
    value: float | None
    prev_value: float | None
    pop_pct: float | None
    prior_year_value: float | None
    yoy_pct: float | None


def _validate_periods_per_year(periods_per_year: int) -> int:
    if not isinstance(periods_per_year, int) or isinstance(periods_per_year, bool):
        raise TypeError("periods_per_year must be an integer")
    if periods_per_year < 1:
        raise ValueError("periods_per_year must be a positive integer")
    return periods_per_year


def _validate_digits(digits: int) -> int:
    if not isinstance(digits, int) or isinstance(digits, bool):
        raise TypeError("digits must be an integer")
    if digits < 0:
        raise ValueError("digits must be non-negative")
    return digits


def _validate_series(series: list[Period]) -> list[Period]:
    points = list(series)
    seen: set[str] = set()
    for point in points:
        if not isinstance(point, Period):
            raise TypeError("series must contain Period instances")
        if not isinstance(point.label, str) or not point.label.strip():
            raise ValueError("each Period.label must be a non-empty string")
        if point.label in seen:
            raise ValueError(f"duplicate label in series: {point.label!r}")
        seen.add(point.label)
        if point.value is None:
            continue
        if not isinstance(point.value, Real) or isinstance(point.value, bool):
            raise TypeError("each Period.value must be numeric or None")
        if not math.isfinite(float(point.value)):
            raise ValueError("each Period.value must be finite or None")
    return points


def _pct_change(current: float | None, baseline: float | None, digits: int) -> float | None:
    """Percentage change of ``current`` from ``baseline``, or ``None``.

    Returns ``None`` when either operand is missing or when the baseline is
    exactly zero - the only cases where a percentage change is undefined.  Uses
    ``abs(baseline)`` in the denominator so the sign of the change tracks the
    direction of movement even when the baseline is negative.
    """
    if current is None or baseline is None:
        return None
    if baseline == 0:
        return None
    return round((float(current) - float(baseline)) / abs(float(baseline)) * 100.0, digits)


def growth_series(
    series: list[Period],
    *,
    periods_per_year: int = 12,
    digits: int = 2,
) -> tuple[Growth, ...]:
    """Compute period-over-period and prior-year growth for a time series.

    Parameters
    ----------
    series:
        The observations, already in chronological order.  May be empty (the
        result is then an empty tuple).  Labels must be unique.  A value of
        ``None`` marks a gap and makes that period an unusable baseline.
    periods_per_year:
        How many periods make up one year - ``12`` for monthly data, ``4`` for
        quarterly, ``52`` for weekly.  Prior-year growth for point *i* compares
        against point ``i - periods_per_year``.  Must be a positive integer.
    digits:
        Decimal places to round each percentage to.  Must be non-negative.

    Returns
    -------
    tuple[Growth, ...]
        One :class:`Growth` per input point, in the same order.  ``pop_pct`` is
        ``None`` for the first point (no prior period) and wherever a baseline
        is ``None`` or zero; ``yoy_pct`` is ``None`` for the first
        ``periods_per_year`` points and under the same baseline rules.
    """
    periods_per_year = _validate_periods_per_year(periods_per_year)
    digits = _validate_digits(digits)
    points = _validate_series(series)

    results: list[Growth] = []
    for index, point in enumerate(points):
        value = None if point.value is None else round(float(point.value), digits)

        prev_value = points[index - 1].value if index >= 1 else None
        prev_value = None if prev_value is None else round(float(prev_value), digits)

        py_index = index - periods_per_year
        prior_year_value = points[py_index].value if py_index >= 0 else None
        prior_year_value = (
            None if prior_year_value is None else round(float(prior_year_value), digits)
        )

        results.append(
            Growth(
                label=point.label,
                value=value,
                prev_value=prev_value,
                pop_pct=_pct_change(value, prev_value, digits),
                prior_year_value=prior_year_value,
                yoy_pct=_pct_change(value, prior_year_value, digits),
            )
        )
    return tuple(results)


def pct_change(current: float | None, baseline: float | None, *, digits: int = 2) -> float | None:
    """Public one-shot percentage change of ``current`` from ``baseline``.

    A thin, validated wrapper over the same rule the series uses: ``None`` when
    either operand is missing or the baseline is zero, otherwise the signed
    percentage change rounded to ``digits`` places.  Handy for a single
    headline comparison outside a full series.
    """
    digits = _validate_digits(digits)
    for name, val in (("current", current), ("baseline", baseline)):
        if val is None:
            continue
        if not isinstance(val, Real) or isinstance(val, bool):
            raise TypeError(f"{name} must be numeric or None")
        if not math.isfinite(float(val)):
            raise ValueError(f"{name} must be finite or None")
    return _pct_change(current, baseline, digits)
