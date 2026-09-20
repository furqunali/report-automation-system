"""Deterministic KPI aggregation for validated report rows."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from .models import ReportRow
from .validation import validate_row


@dataclass(frozen=True)
class KPIResult:
    rows: int
    total_sales: float
    average_sale: float
    sites: int
    products: int
    top_site: str | None
    top_product: str | None


def aggregate_kpis(rows: list[ReportRow]) -> KPIResult:
    """Validate rows and calculate stable dashboard-level KPIs."""
    valid: list[ReportRow] = []
    for row in rows:
        validate_row(row)
        if not isfinite(row.sales):
            raise ValueError("sales must be finite")
        valid.append(row)

    total = round(sum(row.sales for row in valid), 2)
    site_totals: dict[str, float] = {}
    product_totals: dict[str, float] = {}
    for row in valid:
        site_totals[row.site] = site_totals.get(row.site, 0.0) + row.sales
        product_totals[row.product] = product_totals.get(row.product, 0.0) + row.sales

    def winner(values: dict[str, float]) -> str | None:
        if not values:
            return None
        return min(values, key=lambda key: (-values[key], key))

    return KPIResult(
        rows=len(valid),
        total_sales=total,
        average_sale=round(total / len(valid), 2) if valid else 0.0,
        sites=len(site_totals),
        products=len(product_totals),
        top_site=winner(site_totals),
        top_product=winner(product_totals),
    )


def site_breakdown(rows: list[ReportRow]) -> dict[str, float]:
    result: dict[str, float] = {}
    for row in rows:
        validate_row(row)
        result[row.site] = round(result.get(row.site, 0.0) + row.sales, 2)
    return dict(sorted(result.items()))


def product_breakdown(rows: list[ReportRow]) -> dict[str, float]:
    result: dict[str, float] = {}
    for row in rows:
        validate_row(row)
        result[row.product] = round(result.get(row.product, 0.0) + row.sales, 2)
    return dict(sorted(result.items()))
