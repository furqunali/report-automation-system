"""Flag outliers in a numeric series by z-score and by modified z-score.

Once a report has a column of numbers, the reviewer's next question is "which
of these are unusual enough to look at?".  The classic answer is the z-score -
how many standard deviations a point sits from the mean.  Its weakness is that
the very outliers it is meant to catch inflate the mean and standard deviation,
masking themselves.  The robust alternative is the *modified* z-score, built on
the median and the median absolute deviation (MAD), which barely moves in the
presence of a few extremes.

This module offers both.  Given a list of :class:`Sample` (a label plus a
finite value) it returns one :class:`Flag` per point, carrying the point's
score and whether it breaches the threshold.  Two entry points:

* :func:`zscore_flags` - standard z-score, ``(x - mean) / stdev``,
* :func:`modified_zscore_flags` - robust, ``0.6745 * (x - median) / MAD``.

Both degrade gracefully when the series has no spread: if every value is
identical (zero standard deviation, or zero MAD) then nothing is an outlier and
every score is ``0.0`` - never a divide-by-zero.  Everything is deterministic
and rounded on output.
"""
from __future__ import annotations

import math
import statistics
from dataclasses import dataclass
from numbers import Real

# Scaling constant that makes the modified z-score comparable to a standard
# z-score for normally distributed data: 0.6745 is the 0.75 quantile of the
# standard normal, i.e. the expected MAD of a unit normal.
_MAD_SCALE = 0.6745


@dataclass(frozen=True)
class Sample:
    """One observation: a non-empty ``label`` and a finite ``value``."""

    label: str
    value: float


@dataclass(frozen=True)
class Flag:
    """The outlier verdict for a single point.

    ``score`` is the (modified) z-score, rounded.  ``is_outlier`` is ``True``
    when ``abs(score)`` meets or exceeds the threshold.  ``direction`` is
    ``"high"`` for a positive breach, ``"low"`` for a negative one, and ``None``
    when the point is not flagged.
    """

    label: str
    value: float
    score: float
    is_outlier: bool
    direction: str | None


def _validate_digits(digits: int) -> int:
    if not isinstance(digits, int) or isinstance(digits, bool):
        raise TypeError("digits must be an integer")
    if digits < 0:
        raise ValueError("digits must be non-negative")
    return digits


def _validate_threshold(threshold: float) -> float:
    if not isinstance(threshold, Real) or isinstance(threshold, bool):
        raise TypeError("threshold must be numeric")
    threshold = float(threshold)
    if not math.isfinite(threshold):
        raise ValueError("threshold must be finite")
    if threshold <= 0:
        raise ValueError("threshold must be positive")
    return threshold


def _validate_series(series: list[Sample]) -> list[Sample]:
    points = list(series)
    seen: set[str] = set()
    for point in points:
        if not isinstance(point, Sample):
            raise TypeError("series must contain Sample instances")
        if not isinstance(point.label, str) or not point.label.strip():
            raise ValueError("each Sample.label must be a non-empty string")
        if point.label in seen:
            raise ValueError(f"duplicate label in series: {point.label!r}")
        seen.add(point.label)
        if not isinstance(point.value, Real) or isinstance(point.value, bool):
            raise TypeError("each Sample.value must be numeric")
        if not math.isfinite(float(point.value)):
            raise ValueError("each Sample.value must be finite")
    return points


def _build_flags(
    points: list[Sample],
    scores: list[float],
    threshold: float,
    digits: int,
) -> tuple[Flag, ...]:
    flags: list[Flag] = []
    for point, score in zip(points, scores):
        is_outlier = abs(score) >= threshold
        if not is_outlier:
            direction = None
        elif score > 0:
            direction = "high"
        else:
            direction = "low"
        flags.append(
            Flag(
                label=point.label,
                value=round(float(point.value), digits),
                score=round(score, digits),
                is_outlier=is_outlier,
                direction=direction,
            )
        )
    return tuple(flags)


def zscore_flags(
    series: list[Sample],
    *,
    threshold: float = 3.0,
    digits: int = 4,
) -> tuple[Flag, ...]:
    """Flag outliers by standard z-score, ``(x - mean) / stdev``.

    Uses the population standard deviation (``statistics.pstdev``) so a single
    fixed series has a well-defined spread without needing ``n - 1`` degrees of
    freedom.

    Parameters
    ----------
    series:
        The observations.  May be empty (result is an empty tuple).  Labels must
        be unique and values finite.
    threshold:
        Positive cutoff on ``abs(score)``; ``3.0`` is the common "three sigma"
        rule.  A point is flagged when its absolute z-score is ``>= threshold``.
    digits:
        Decimal places for scores and echoed values.

    Returns
    -------
    tuple[Flag, ...]
        One :class:`Flag` per point, in order.  When the series has zero spread
        (all values equal, or a single point) every score is ``0.0`` and
        nothing is flagged.
    """
    threshold = _validate_threshold(threshold)
    digits = _validate_digits(digits)
    points = _validate_series(series)
    if not points:
        return ()

    raw = [float(p.value) for p in points]
    mean = statistics.fmean(raw)
    stdev = statistics.pstdev(raw)
    if stdev == 0:
        scores = [0.0] * len(raw)
    else:
        scores = [(x - mean) / stdev for x in raw]
    return _build_flags(points, scores, threshold, digits)


def modified_zscore_flags(
    series: list[Sample],
    *,
    threshold: float = 3.5,
    digits: int = 4,
) -> tuple[Flag, ...]:
    """Flag outliers by the robust modified z-score (MAD-based).

    Computes ``0.6745 * (x - median) / MAD`` where ``MAD`` is the median of the
    absolute deviations from the median.  Because it uses the median rather than
    the mean, a few extreme points cannot hide themselves by inflating the
    spread - the standard reason to prefer this over a plain z-score for
    outlier detection.

    Parameters
    ----------
    series:
        The observations.  May be empty.  Labels must be unique, values finite.
    threshold:
        Positive cutoff on ``abs(score)``; Iglewicz & Hoaglin's classic
        recommendation is ``3.5``.
    digits:
        Decimal places for scores and echoed values.

    Returns
    -------
    tuple[Flag, ...]
        One :class:`Flag` per point, in order.  When the MAD is zero (more than
        half the values are identical) there is no robust spread to measure, so
        every score is ``0.0`` and nothing is flagged.
    """
    threshold = _validate_threshold(threshold)
    digits = _validate_digits(digits)
    points = _validate_series(series)
    if not points:
        return ()

    raw = [float(p.value) for p in points]
    median = statistics.median(raw)
    mad = statistics.median([abs(x - median) for x in raw])
    if mad == 0:
        scores = [0.0] * len(raw)
    else:
        scores = [_MAD_SCALE * (x - median) / mad for x in raw]
    return _build_flags(points, scores, threshold, digits)
