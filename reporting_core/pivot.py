"""Pivot / group-by aggregation over the consolidated report master.

The management roll-up in :mod:`reporting_core.kpi` answers one fixed question -
"totals per site, plus the leading products".  Analysts routinely need to slice
the same validated ``ReportRow`` master along *other* dimensions: sales by
category, average basket by status, the row count per product, the smallest and
largest ticket per site.  Re-deriving each of those by hand is exactly where
copy-paste bugs creep into a monthly report.

This module provides one deterministic primitive - :func:`pivot` - that groups
the master by one or more dimensions (``site``, ``category``, ``product``,
``status``) and reduces a numeric metric (``sales`` or ``quantity``) with a
chosen aggregation (``sum``, ``mean``, ``count``, ``min`` or ``max``).  Every
row is validated up front, groups come back in a stable key order, and floats
are rounded consistently, so the same master always yields the same table -
safe to diff in tests and to hand straight to the dashboard.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .models import ReportRow
from .validation import validate_row

# Categorical fields a master may be grouped by.
_DIMENSIONS = ("site", "category", "product", "status")
# Numeric fields that can be reduced.
_METRICS = ("sales", "quantity")
# Supported reductions. ``count`` is the row tally and needs no metric.
_AGGREGATIONS = ("sum", "mean", "count", "min", "max")


@dataclass(frozen=True)
class PivotGroup:
    """One group in a pivot result.

    ``key`` is the tuple of dimension values in the same order as the ``by``
    argument passed to :func:`pivot` - always a tuple, even for a single
    dimension, so callers can index it uniformly.  ``count`` is the number of
    rows that fell into the group and ``value`` is the aggregated metric (equal
    to ``count`` when the aggregation is ``"count"``).
    """

    key: tuple[str, ...]
    count: int
    value: float


@dataclass(frozen=True)
class Pivot:
    """The full pivot table over one consolidated master."""

    by: tuple[str, ...]
    metric: str | None
    agg: str
    groups: tuple[PivotGroup, ...]


def _normalize_by(by: str | list[str] | tuple[str, ...]) -> tuple[str, ...]:
    """Coerce the ``by`` argument to a validated tuple of dimension names."""
    if isinstance(by, str):
        dims: tuple[str, ...] = (by,)
    elif isinstance(by, (list, tuple)):
        dims = tuple(by)
    else:
        raise TypeError("by must be a dimension name or a sequence of them")

    if not dims:
        raise ValueError("by must name at least one dimension")
    seen: set[str] = set()
    for dim in dims:
        if dim not in _DIMENSIONS:
            raise ValueError(f"by dimensions must each be one of {_DIMENSIONS}")
        if dim in seen:
            raise ValueError(f"duplicate dimension in by: {dim!r}")
        seen.add(dim)
    return dims


def _reduce(agg: str, values: list[float]) -> float:
    """Reduce a non-empty list of metric values with the named aggregation."""
    if agg == "count":
        return float(len(values))
    if agg == "sum":
        return round(math.fsum(values), 2)
    if agg == "mean":
        return round(math.fsum(values) / len(values), 2)
    if agg == "min":
        return round(min(values), 2)
    if agg == "max":
        return round(max(values), 2)
    raise ValueError(f"agg must be one of {_AGGREGATIONS}")  # pragma: no cover


def pivot(
    rows: list[ReportRow],
    *,
    by: str | list[str] | tuple[str, ...],
    metric: str | None = None,
    agg: str = "sum",
) -> Pivot:
    """Group ``rows`` by one or more dimensions and reduce a metric.

    Parameters
    ----------
    rows:
        The consolidated master - a list of ``ReportRow`` objects.  Every row is
        validated with :func:`reporting_core.validation.validate_row` first, so
        malformed input fails fast rather than skewing an aggregate.
    by:
        A single dimension name (``"site"``, ``"category"``, ``"product"`` or
        ``"status"``) or a sequence of them.  Grouping is by the tuple of those
        fields, in the order given.  Names must be unique.
    metric:
        The numeric field to reduce - ``"sales"`` or ``"quantity"``.  Required
        for every aggregation except ``"count"``; it must be omitted (or left
        ``None``) when ``agg`` is ``"count"``, which tallies rows and needs no
        metric.
    agg:
        The reduction to apply: ``"sum"``, ``"mean"``, ``"count"``, ``"min"`` or
        ``"max"``.  Defaults to ``"sum"``.

    Returns
    -------
    Pivot
        One :class:`PivotGroup` per distinct key, sorted ascending by key so the
        output is stable and diff-friendly.  An empty ``rows`` list yields a
        ``Pivot`` with no groups (the ``by``/``metric``/``agg`` arguments are
        still validated).  ``sum``, ``mean``, ``min`` and ``max`` values are
        rounded to two decimals; ``count`` values are whole numbers.

    Raises
    ------
    ValueError
        If ``by`` is empty or names an unknown/duplicate dimension, if ``agg``
        is unknown, if ``metric`` is missing for a non-``count`` aggregation, if
        ``metric`` is supplied for ``count``, or if ``metric`` names an unknown
        field.
    TypeError
        If ``by`` is neither a string nor a sequence of strings.
    """
    dims = _normalize_by(by)

    if agg not in _AGGREGATIONS:
        raise ValueError(f"agg must be one of {_AGGREGATIONS}")

    if agg == "count":
        if metric is not None:
            raise ValueError("metric must be omitted when agg is 'count'")
    else:
        if metric is None:
            raise ValueError(f"metric is required for agg {agg!r}")
        if metric not in _METRICS:
            raise ValueError(f"metric must be one of {_METRICS}")

    # Validate before grouping so a bad row never lands in a bucket.
    for row in rows:
        validate_row(row)

    # Preserve first-seen order of keys; sort at the end for a stable result.
    buckets: dict[tuple[str, ...], list[float]] = {}
    for row in rows:
        key = tuple(getattr(row, dim) for dim in dims)
        # For count we never read a metric, so store a placeholder to keep the
        # per-group length correct without touching a numeric field.
        value = 0.0 if metric is None else float(getattr(row, metric))
        buckets.setdefault(key, []).append(value)

    groups = tuple(
        PivotGroup(key=key, count=len(values), value=_reduce(agg, values))
        for key, values in sorted(buckets.items())
    )

    return Pivot(by=dims, metric=metric, agg=agg, groups=groups)


def top_groups(result: Pivot, *, top_n: int = 5) -> tuple[PivotGroup, ...]:
    """Return the ``top_n`` groups with the largest ``value``.

    Ranked by ``value`` descending, with ties broken by ``key`` ascending so the
    ordering is fully deterministic.  Useful for "biggest categories" or
    "busiest sites" tables built straight from a :func:`pivot` result.
    """
    if not isinstance(top_n, int) or isinstance(top_n, bool) or top_n < 1:
        raise ValueError("top_n must be a positive integer")

    ranked = sorted(result.groups, key=lambda g: (-g.value, g.key))
    return tuple(ranked[:top_n])
