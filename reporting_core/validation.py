import math

from .models import ReportRow, ReportSummary


def _finite(value: float) -> bool:
    return math.isfinite(value)


def validate_row(row: ReportRow) -> None:
    if not row.site.strip():
        raise ValueError("site must be non-empty")
    if not row.product.strip():
        raise ValueError("product must be non-empty")
    if row.quantity < 0 or not _finite(row.quantity):
        raise ValueError("quantity must be finite and non-negative")
    if row.sales < 0 or not _finite(row.sales):
        raise ValueError("sales must be finite and non-negative")
    if row.status not in ("Active", "No Movement"):
        raise ValueError("status must be Active or No Movement")


def validate_summary(summary: ReportSummary) -> None:
    if summary.total_sales < 0 or not _finite(summary.total_sales):
        raise ValueError("total_sales must be finite and non-negative")
    if summary.total_quantity < 0 or not _finite(summary.total_quantity):
        raise ValueError("total_quantity must be finite and non-negative")
    if summary.active_products < 0 or summary.no_movement_products < 0:
        raise ValueError("product counts must be non-negative")
