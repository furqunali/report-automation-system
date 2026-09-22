"""Derived metrics for report-total reconciliation."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite

from reporting_core.reconciliation import ReconciliationResult


@dataclass(frozen=True)
class ReconciliationMetrics:
    absolute_delta: float
    relative_delta: float | None
    within_tolerance: bool

def build_reconciliation_metrics(result: ReconciliationResult) -> ReconciliationMetrics:
    delta = float(result.delta)
    expected = float(result.expected_sales)
    if not isfinite(delta) or not isfinite(expected):
        raise ValueError("reconciliation values must be finite")
    relative = None if expected == 0 else round(delta / abs(expected), 6)
    return ReconciliationMetrics(
        absolute_delta=round(abs(delta), 2),
        relative_delta=relative,
        within_tolerance=result.balanced,
    )
