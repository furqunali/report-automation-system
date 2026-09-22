"""Period-over-period comparison of management reports.

Given the :class:`~reporting_core.kpi.ManagementKPIs` roll-up for two reporting
periods - typically the current month and the month before - this module
produces month-over-month **deltas** and **percent change** for each headline
KPI and for every location, plus a ranked view of the biggest movers.

The percent-change convention is applied consistently everywhere:

* ``previous != 0``  -> ``round((current - previous) / previous * 100, 2)``.
* ``previous == 0`` and ``current == 0`` -> ``0.0`` (flat, nothing changed).
* ``previous == 0`` and ``current != 0`` -> ``None`` (growth from a zero base
  is mathematically undefined; a report must not print "inf%" or invent a
  number the reader would mistake for a real rate).

A location that reported in only one of the two periods is not silently
dropped: it is carried through with the missing side treated as zero and
flagged as ``"new"`` (only in the current period) or ``"dropped"`` (only in
the previous period), so a store that stopped filing is impossible to miss.

Everything is deterministic - the same pair of reports always yields the same
comparison - so it is safe to diff in tests and hand straight to the dashboard.
"""
from __future__ import annotations

from dataclasses import dataclass

from .kpi import ManagementKPIs


@dataclass(frozen=True)
class MetricDelta:
    """Month-over-month change for a single scalar KPI."""

    metric: str
    current: float
    previous: float
    delta: float
    pct_change: float | None


@dataclass(frozen=True)
class LocationDelta:
    """Month-over-month change in sales and quantity for one site.

    ``presence`` is ``"continuing"`` when the site reported in both periods,
    ``"new"`` when it appears only in the current period, and ``"dropped"``
    when it appears only in the previous period.
    """

    site: str
    presence: str
    current_sales: float
    previous_sales: float
    sales_delta: float
    sales_pct_change: float | None
    current_quantity: float
    previous_quantity: float
    quantity_delta: float
    quantity_pct_change: float | None


@dataclass(frozen=True)
class PeriodComparison:
    """The full current-vs-previous comparison of two management reports."""

    current_label: str
    previous_label: str
    metrics: tuple[MetricDelta, ...]
    locations: tuple[LocationDelta, ...]


# Headline scalar KPIs compared in a fixed, reader-friendly order. Each entry
# maps a display name to the ``ManagementKPIs`` attribute it is read from.
_SCALAR_METRICS: tuple[tuple[str, str], ...] = (
    ("total_sales", "total_sales"),
    ("total_quantity", "total_quantity"),
    ("active_products", "active_products"),
    ("no_movement_products", "no_movement_products"),
    ("site_count", "site_count"),
    ("product_count", "product_count"),
)


def _pct_change(current: float, previous: float) -> float | None:
    """Percent change from ``previous`` to ``current`` per the module rule.

    Returns ``None`` when the previous value is zero but the current value is
    not (undefined growth from a zero base), and ``0.0`` when both are zero.
    """
    if previous == 0:
        return 0.0 if current == 0 else None
    return round((current - previous) / previous * 100, 2)


def _metric_delta(metric: str, current: float, previous: float) -> MetricDelta:
    return MetricDelta(
        metric=metric,
        current=round(float(current), 2),
        previous=round(float(previous), 2),
        delta=round(float(current) - float(previous), 2),
        pct_change=_pct_change(float(current), float(previous)),
    )


def _validate_label(label: str, name: str) -> str:
    if not isinstance(label, str):
        raise TypeError(f"{name} must be a string")
    if not label.strip():
        raise ValueError(f"{name} must be non-empty")
    return label


def compare_periods(
    current: ManagementKPIs,
    previous: ManagementKPIs,
    *,
    current_label: str = "current",
    previous_label: str = "previous",
) -> PeriodComparison:
    """Compare two management reports period over period.

    Parameters
    ----------
    current:
        The management report for the later period (e.g. this month).
    previous:
        The management report for the earlier period (e.g. last month).
    current_label, previous_label:
        Human-readable names for the two periods (e.g. ``"2026-09"`` and
        ``"2026-08"``). Both must be non-empty strings and must differ, so a
        rendered comparison can never mislabel which column is which.

    Returns
    -------
    PeriodComparison
        Per-KPI ``MetricDelta`` rows (in a fixed order) and one
        ``LocationDelta`` per site seen in either period, sorted by site name.
    """
    if not isinstance(current, ManagementKPIs) or not isinstance(previous, ManagementKPIs):
        raise TypeError("current and previous must be ManagementKPIs instances")

    current_label = _validate_label(current_label, "current_label")
    previous_label = _validate_label(previous_label, "previous_label")
    if current_label == previous_label:
        raise ValueError("current_label and previous_label must differ")

    metrics = tuple(
        _metric_delta(name, getattr(current, attr), getattr(previous, attr))
        for name, attr in _SCALAR_METRICS
    )

    cur_sites = {loc.site: loc for loc in current.locations}
    prev_sites = {loc.site: loc for loc in previous.locations}

    locations: list[LocationDelta] = []
    for site in sorted(set(cur_sites) | set(prev_sites)):
        cur = cur_sites.get(site)
        prev = prev_sites.get(site)
        if cur is not None and prev is not None:
            presence = "continuing"
        elif cur is not None:
            presence = "new"
        else:
            presence = "dropped"

        cur_sales = round(cur.sales, 2) if cur is not None else 0.0
        prev_sales = round(prev.sales, 2) if prev is not None else 0.0
        cur_qty = round(cur.quantity, 2) if cur is not None else 0.0
        prev_qty = round(prev.quantity, 2) if prev is not None else 0.0

        locations.append(
            LocationDelta(
                site=site,
                presence=presence,
                current_sales=cur_sales,
                previous_sales=prev_sales,
                sales_delta=round(cur_sales - prev_sales, 2),
                sales_pct_change=_pct_change(cur_sales, prev_sales),
                current_quantity=cur_qty,
                previous_quantity=prev_qty,
                quantity_delta=round(cur_qty - prev_qty, 2),
                quantity_pct_change=_pct_change(cur_qty, prev_qty),
            )
        )

    return PeriodComparison(
        current_label=current_label,
        previous_label=previous_label,
        metrics=metrics,
        locations=tuple(locations),
    )


def top_movers(
    comparison: PeriodComparison,
    *,
    top_n: int = 5,
) -> tuple[LocationDelta, ...]:
    """Return the locations with the largest absolute sales swing.

    Ranked by ``abs(sales_delta)`` descending, with ties broken by site name so
    the ordering is deterministic. Sites whose sales did not move at all are
    excluded - a "top movers" table should not be padded with flat rows.
    """
    if not isinstance(top_n, int) or isinstance(top_n, bool) or top_n < 1:
        raise ValueError("top_n must be a positive integer")

    movers = [loc for loc in comparison.locations if loc.sales_delta != 0]
    movers.sort(key=lambda loc: (-abs(loc.sales_delta), loc.site))
    return tuple(movers[:top_n])
