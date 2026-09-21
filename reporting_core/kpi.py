"""Management-level KPIs over the consolidated master.

Where :mod:`reporting_core.kpis` produces flat, dashboard-tile numbers,
this module rolls the same validated ``ReportRow`` master up into the view a
manager reads: company totals, a per-location subtotal table, variance against
an optional budget, and the leading products by sales.

Everything is deterministic and validated up front, so the same master always
yields the same report - safe to diff in tests and in the dashboard handoff.
"""
from __future__ import annotations

from dataclasses import dataclass
from numbers import Real
from typing import Mapping

from .models import ReportRow
from .validation import validate_row


@dataclass(frozen=True)
class LocationSubtotal:
    """Per-site roll-up, optionally scored against that site's budget."""

    site: str
    sales: float
    quantity: float
    products: int
    budget: float | None
    variance: float | None
    variance_pct: float | None


@dataclass(frozen=True)
class ProductRank:
    """A single product's contribution, used for the "top products" table."""

    product: str
    sales: float
    quantity: float


@dataclass(frozen=True)
class ManagementKPIs:
    """The full management report over one consolidated master."""

    row_count: int
    total_sales: float
    total_quantity: float
    active_products: int
    no_movement_products: int
    site_count: int
    product_count: int
    total_budget: float | None
    total_variance: float | None
    total_variance_pct: float | None
    locations: tuple[LocationSubtotal, ...]
    top_products: tuple[ProductRank, ...]


def _clean_budget(budget: Mapping[str, float] | None) -> dict[str, float]:
    """Validate and copy the optional site -> budgeted-sales mapping."""
    if budget is None:
        return {}
    cleaned: dict[str, float] = {}
    for site, value in budget.items():
        if not str(site).strip():
            raise ValueError("budget site must be non-empty")
        if not isinstance(value, Real) or isinstance(value, bool):
            raise TypeError("budget values must be numeric")
        amount = float(value)
        if amount < 0 or amount != amount or amount in (float("inf"), float("-inf")):
            raise ValueError("budget values must be finite and non-negative")
        cleaned[str(site)] = amount
    return cleaned


def _variance(sales: float, budget: float | None) -> tuple[float | None, float | None]:
    """Return (variance, variance_pct) for a sales figure against a budget."""
    if budget is None:
        return None, None
    variance = round(sales - budget, 2)
    pct = round(variance / budget * 100, 2) if budget > 0 else None
    return variance, pct


def compute_management_kpis(
    rows: list[ReportRow],
    *,
    budget: Mapping[str, float] | None = None,
    top_n: int = 5,
) -> ManagementKPIs:
    """Roll a validated ``ReportRow`` master up into a management report.

    Parameters
    ----------
    rows:
        The consolidated master - a list of ``ReportRow`` objects. Every row is
        validated with :func:`reporting_core.validation.validate_row` first, so
        malformed input fails fast rather than skewing the totals.
    budget:
        Optional mapping of site -> budgeted sales. When supplied, each location
        (and the company total) gains a ``variance``/``variance_pct``. A site
        that is budgeted but reported nothing still appears, with zero sales and
        the full budget as an unfavorable variance - a reporting gap managers
        need to see rather than have silently dropped.
    top_n:
        How many leading products to return, ranked by sales (ties broken by
        product name). Must be a positive integer.
    """
    if not isinstance(top_n, int) or isinstance(top_n, bool) or top_n < 1:
        raise ValueError("top_n must be a positive integer")

    budgets = _clean_budget(budget)

    total_sales = 0.0
    total_quantity = 0.0
    active = 0
    no_movement = 0

    site_sales: dict[str, float] = {}
    site_quantity: dict[str, float] = {}
    site_products: dict[str, set[str]] = {}
    product_sales: dict[str, float] = {}
    product_quantity: dict[str, float] = {}

    for row in rows:
        validate_row(row)
        total_sales += row.sales
        total_quantity += row.quantity
        if row.status == "No Movement":
            no_movement += 1
        else:
            active += 1

        site_sales[row.site] = site_sales.get(row.site, 0.0) + row.sales
        site_quantity[row.site] = site_quantity.get(row.site, 0.0) + row.quantity
        site_products.setdefault(row.site, set()).add(row.product)

        product_sales[row.product] = product_sales.get(row.product, 0.0) + row.sales
        product_quantity[row.product] = product_quantity.get(row.product, 0.0) + row.quantity

    # Locations = every site that reported OR was budgeted, so a budgeted store
    # that filed nothing surfaces as a zero-sales gap instead of vanishing.
    site_names = sorted(set(site_sales) | set(budgets))
    locations: list[LocationSubtotal] = []
    for site in site_names:
        sales = round(site_sales.get(site, 0.0), 2)
        site_budget = budgets.get(site) if budgets else None
        variance, variance_pct = _variance(sales, site_budget)
        locations.append(
            LocationSubtotal(
                site=site,
                sales=sales,
                quantity=round(site_quantity.get(site, 0.0), 2),
                products=len(site_products.get(site, set())),
                budget=site_budget,
                variance=variance,
                variance_pct=variance_pct,
            )
        )

    ranked = sorted(product_sales, key=lambda p: (-product_sales[p], p))
    top_products = tuple(
        ProductRank(
            product=p,
            sales=round(product_sales[p], 2),
            quantity=round(product_quantity[p], 2),
        )
        for p in ranked[:top_n]
    )

    total_sales = round(total_sales, 2)
    total_budget = round(sum(budgets.values()), 2) if budgets else None
    total_variance, total_variance_pct = _variance(total_sales, total_budget)

    return ManagementKPIs(
        row_count=len(rows),
        total_sales=total_sales,
        total_quantity=round(total_quantity, 2),
        active_products=active,
        no_movement_products=no_movement,
        site_count=len(site_sales),
        product_count=len(product_sales),
        total_budget=total_budget,
        total_variance=total_variance,
        total_variance_pct=total_variance_pct,
        locations=tuple(locations),
        top_products=top_products,
    )
