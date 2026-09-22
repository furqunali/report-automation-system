"""Rolling-average / moving-window trend helper over a time-ordered series.

Monthly management reports produce one headline number per period - total
sales, total quantity, a defect rate - and the interesting question is rarely
"what was this month?" but "how does this month sit against the recent trend?".
A single raw value swings with seasonality and one-off events; a trailing
moving average smooths that noise into a line a reader can actually reason
about.

This module turns a time-ordered series of :class:`TrendPoint` values into a
:class:`RollingWindow` per period, each carrying:

* the raw ``value`` at that period,
* the trailing **moving average** over the last ``window`` points (``None``
  while the window is still warming up, so a report never prints an average
  computed from fewer points than the caller asked for),
* the ``delta`` of the raw value from that average - how far this period sits
  above or below its own recent trend.

The averaging is strictly **trailing** (causal): the value at period *i* only
ever averages periods *<= i*, never future ones. That matters for reports,
where a centred window would leak next month's number into this month's figure.

On top of that, :func:`crossovers` flags the periods where the raw value
crosses its moving average - the classic, robust signal of a trend reversal.

Everything is deterministic and validated up front, so the same series always
yields the same output - safe to diff in tests and hand straight to the
dashboard.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real


@dataclass(frozen=True)
class TrendPoint:
    """One observation in a time-ordered series.

    ``period`` is a human-readable label (e.g. ``"2026-08"``) and must be a
    non-empty string; ``value`` must be a finite number.  The series is assumed
    to already be in chronological order - this module never reorders it, so
    the caller stays in control of what "trailing" means.
    """

    period: str
    value: float


@dataclass(frozen=True)
class RollingWindow:
    """The trailing moving-average view of a single period.

    ``average`` is ``None`` until at least ``min_periods`` observations are
    available, at which point it is the mean of the trailing ``window_size``
    values.  ``delta`` is ``value - average`` (rounded), or ``None`` whenever
    ``average`` is - so a caller can always tell "no trend yet" from "on trend".
    """

    period: str
    value: float
    average: float | None
    window_size: int
    delta: float | None


def _validate_window(window: int) -> int:
    if not isinstance(window, int) or isinstance(window, bool):
        raise TypeError("window must be an integer")
    if window < 1:
        raise ValueError("window must be a positive integer")
    return window


def _validate_min_periods(min_periods: int | None, window: int) -> int:
    if min_periods is None:
        return window
    if not isinstance(min_periods, int) or isinstance(min_periods, bool):
        raise TypeError("min_periods must be an integer")
    if min_periods < 1:
        raise ValueError("min_periods must be a positive integer")
    if min_periods > window:
        raise ValueError("min_periods must not exceed window")
    return min_periods


def _validate_series(series: list[TrendPoint]) -> list[TrendPoint]:
    points = list(series)
    seen: set[str] = set()
    for point in points:
        if not isinstance(point, TrendPoint):
            raise TypeError("series must contain TrendPoint instances")
        if not isinstance(point.period, str) or not point.period.strip():
            raise ValueError("each TrendPoint.period must be a non-empty string")
        if point.period in seen:
            raise ValueError(f"duplicate period in series: {point.period!r}")
        seen.add(point.period)
        if not isinstance(point.value, Real) or isinstance(point.value, bool):
            raise TypeError("each TrendPoint.value must be numeric")
        if not math.isfinite(float(point.value)):
            raise ValueError("each TrendPoint.value must be finite")
    return points


def rolling_average(
    series: list[TrendPoint],
    *,
    window: int,
    min_periods: int | None = None,
) -> tuple[RollingWindow, ...]:
    """Compute the trailing moving average of a time-ordered series.

    Parameters
    ----------
    series:
        The observations, already in chronological order.  May be empty (the
        result is then an empty tuple).  Every point is validated up front, so
        malformed input fails fast rather than silently skewing an average.
        Period labels must be unique - a repeated label almost always means a
        merge bug upstream, and would make the output impossible to line up.
    window:
        The number of trailing points to average, inclusive of the current one.
        Must be a positive integer.  ``window=1`` degenerates to the raw series
        (every average equals its own value).
    min_periods:
        The smallest number of observations for which an average is emitted.
        Defaults to ``window`` (no average until the window is completely
        full).  Set it lower to get an early, partial-window average during the
        warm-up.  Must be an integer in ``[1, window]``.

    Returns
    -------
    tuple[RollingWindow, ...]
        One :class:`RollingWindow` per input point, in the same order.  For
        point *i* the average covers points ``[max(0, i-window+1) .. i]``;
        ``window_size`` is how many points that actually spans (it grows from
        ``1`` up to ``window`` and then holds steady).  When fewer than
        ``min_periods`` points are available the ``average`` and ``delta`` are
        ``None`` but ``window_size`` still reflects what was seen.
    """
    window = _validate_window(window)
    min_periods = _validate_min_periods(min_periods, window)
    points = _validate_series(series)

    results: list[RollingWindow] = []
    for index, point in enumerate(points):
        start = max(0, index - window + 1)
        span = points[start : index + 1]
        window_size = len(span)
        value = round(float(point.value), 2)
        if window_size >= min_periods:
            average = round(sum(float(p.value) for p in span) / window_size, 2)
            delta = round(value - average, 2)
        else:
            average = None
            delta = None
        results.append(
            RollingWindow(
                period=point.period,
                value=value,
                average=average,
                window_size=window_size,
                delta=delta,
            )
        )
    return tuple(results)


@dataclass(frozen=True)
class Crossover:
    """A period where the raw value crossed its trailing moving average.

    ``direction`` is ``"above"`` when the value moved from at-or-below the
    average to strictly above it (an upturn against the trend), and ``"below"``
    for the reverse (a downturn).
    """

    period: str
    direction: str
    value: float
    average: float


def crossovers(windows: tuple[RollingWindow, ...]) -> tuple[Crossover, ...]:
    """Detect where the raw value crosses its moving average.

    A crossover is the moment the sign of ``delta`` (value minus average)
    flips between two consecutive periods that both have an average.  It is the
    standard, noise-tolerant signal that a series has turned: a value pushing
    above its own trailing trend, or slipping below it.

    Only periods whose ``average`` is not ``None`` are considered, and the
    comparison walks *consecutive* such periods, so a warm-up gap in the middle
    of the series never fabricates a crossover across it.  A period sitting
    exactly on its average (``delta == 0``) is treated as neither above nor
    below: it neither triggers a crossover nor resets the last-known side, so a
    single flat month between two rises is not mistaken for a reversal.

    Parameters
    ----------
    windows:
        The output of :func:`rolling_average` (or any tuple of
        :class:`RollingWindow`).

    Returns
    -------
    tuple[Crossover, ...]
        The crossover periods in chronological order.  Empty when the series
        never crosses its average.
    """
    crosses: list[Crossover] = []
    last_side: int | None = None
    for win in windows:
        if not isinstance(win, RollingWindow):
            raise TypeError("windows must contain RollingWindow instances")
        if win.average is None or win.delta is None:
            continue
        if win.delta > 0:
            side = 1
        elif win.delta < 0:
            side = -1
        else:
            # Exactly on the average: not a side, and does not reset state.
            continue
        if last_side is not None and side != last_side:
            crosses.append(
                Crossover(
                    period=win.period,
                    direction="above" if side > 0 else "below",
                    value=win.value,
                    average=win.average,
                )
            )
        last_side = side
    return tuple(crosses)
