"""Summarize reconciliation outcomes for automation logs."""
from __future__ import annotations
from dataclasses import dataclass
from reporting_core.reconciliation import ReconciliationResult, reconcile_sales

@dataclass(frozen=True)
class ReconciliationSummary:
    balanced: bool
    delta: float
    message: str

def summarize_reconciliation(expected_sales: float, observed_sales: float, *, tolerance: float = 0.01) -> ReconciliationSummary:
    result: ReconciliationResult = reconcile_sales(expected_sales, observed_sales, tolerance=tolerance)
    message = "sales totals balanced" if result.balanced else "sales totals require review"
    return ReconciliationSummary(result.balanced, result.delta, message)
