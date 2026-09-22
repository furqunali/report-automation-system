"""IQR-based outlier detection to complement the z-score anomaly checks.

:mod:`reporting_core.anomalies` catches rows that break hard validation rules
(negative values, unrecognized status).  Statistical outliers are a different
problem: every value is individually valid, yet a handful sit far outside the
bulk of the distribution and quietly skew site subtotals and top-product
tables.

This module flags those points with Tukey's fences on the inter-quartile
range (IQR) - a robust, distribution-free complement to the z-score.  Because
the fences are built from quartiles rather than the mean and standard
deviation, a single enormous value cannot inflate the threshold and mask
itself: the exact failure mode that makes plain z-scores unreliable on the
small monthly report batches this system handles.

Everything is deterministic and validated up front, so the same master always
yields the same outliers - safe to diff in tests and in the dashboard handoff.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real

from .models import ReportRow
from .validation import validate_row

_METRICS = ("sales", "quantity")


@dataclass(frozen=True)
class IQRBounds:
    """The quartile summary and Tukey fences for one metric's distribution."""

    q1: float
    median: float
    q3: float
    iqr: float
    lower: float
    upper: float


@dataclass(frozen=True)
class Outlier:
    """A single row whose metric value falls outside the IQR fences."""

    row_index: int
    site: str
    product: str
    metric: str
    value: float
    side: str  # "low" or "high"
    fence: float  # the bound the value crossed
    severity: str  # "mild" or "extreme"


def _quantile(ordered: list[float], q: float) -> float:
    """Linear-interpolated quantile of already-sorted ``ordered`` (numpy type 7).

    ``q`` is a fraction in ``[0, 1]``.  With a single point the quantile is that
    point; otherwise the rank ``(n - 1) * q`` is split into an integer base and
    a fractional weight and interpolated between the two straddling samples.
    """
    n = len(ordered)
    if n == 1:
        return ordered[0]
    pos = (n - 1) * q
    base = math.floor(pos)
    frac = pos - base
    if base + 1 >= n:
        return ordered[base]
    return ordered[base] + frac * (ordered[base + 1] - ordered[base])


def iqr_bounds(values: list[float], *, k: float = 1.5) -> IQRBounds:
    """Compute the quartiles and Tukey fences for ``values``.

    Parameters
    ----------
    values:
        A non-empty list of finite numbers.
    k:
        The fence multiplier.  ``lower = Q1 - k*IQR`` and
        ``upper = Q3 + k*IQR``.  The classic Tukey value is ``1.5`` for mild
        outliers and ``3.0`` for extreme ones.  Must be a non-negative,
        finite number.
    """
    if not isinstance(k, Real) or isinstance(k, bool):
        raise TypeError("k must be numeric")
    k = float(k)
    if k < 0 or not math.isfinite(k):
        raise ValueError("k must be finite and non-negative")
    if not values:
        raise ValueError("values must be non-empty")

    numbers: list[float] = []
    for value in values:
        if not isinstance(value, Real) or isinstance(value, bool):
            raise TypeError("values must be numeric")
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("values must be finite")
        numbers.append(number)

    ordered = sorted(numbers)
    q1 = _quantile(ordered, 0.25)
    median = _quantile(ordered, 0.5)
    q3 = _quantile(ordered, 0.75)
    iqr = q3 - q1
    return IQRBounds(
        q1=q1,
        median=median,
        q3=q3,
        iqr=iqr,
        lower=q1 - k * iqr,
        upper=q3 + k * iqr,
    )


def find_outliers(
    rows: list[ReportRow],
    *,
    metric: str = "sales",
    k: float = 1.5,
    extreme_k: float = 3.0,
    min_points: int = 4,
) -> list[Outlier]:
    """Flag rows whose ``metric`` value falls outside the IQR fences.

    Parameters
    ----------
    rows:
        The consolidated master.  Every row is validated with
        :func:`reporting_core.validation.validate_row` first, so malformed
        input fails fast rather than corrupting the distribution.
    metric:
        Which numeric field to analyze - ``"sales"`` or ``"quantity"``.
    k:
        Fence multiplier for flagging a value as an outlier (default ``1.5``).
    extreme_k:
        Wider fence multiplier used only to label a flagged value ``"extreme"``
        rather than ``"mild"``.  Must be greater than or equal to ``k``.
    min_points:
        The smallest sample for which fences are trustworthy.  Below this the
        quartiles are too unstable to separate signal from noise, so no
        outliers are reported.  Must be at least ``2``.

    Returns
    -------
    A list of :class:`Outlier` in ascending ``row_index`` order.  A value that
    equals a fence exactly is *not* flagged; only values strictly beyond it are.
    When ``IQR`` is zero (a near-constant column) the fences collapse onto the
    quartiles, so only rows differing from the constant are reported.
    """
    if metric not in _METRICS:
        raise ValueError(f"metric must be one of {_METRICS}")
    if not isinstance(min_points, int) or isinstance(min_points, bool) or min_points < 2:
        raise ValueError("min_points must be an integer >= 2")
    if not isinstance(extreme_k, Real) or isinstance(extreme_k, bool):
        raise TypeError("extreme_k must be numeric")
    if float(extreme_k) < float(k):
        raise ValueError("extreme_k must be >= k")

    for row in rows:
        validate_row(row)

    if len(rows) < min_points:
        return []

    values = [float(getattr(row, metric)) for row in rows]
    bounds = iqr_bounds(values, k=k)
    extreme = iqr_bounds(values, k=extreme_k)

    outliers: list[Outlier] = []
    for index, (row, value) in enumerate(zip(rows, values)):
        if value < bounds.lower:
            side, fence = "low", bounds.lower
            severity = "extreme" if value < extreme.lower else "mild"
        elif value > bounds.upper:
            side, fence = "high", bounds.upper
            severity = "extreme" if value > extreme.upper else "mild"
        else:
            continue
        outliers.append(
            Outlier(
                row_index=index,
                site=row.site,
                product=row.product,
                metric=metric,
                value=value,
                side=side,
                fence=round(fence, 2),
                severity=severity,
            )
        )
    return outliers
