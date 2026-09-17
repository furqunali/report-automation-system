"""Deterministic reconciliation checks for report totals."""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose

@dataclass(frozen=True)
class ReconciliationResult:
    expected_sales: float
    observed_sales: float
    delta: float
    balanced: bool

def reconcile_sales(expected_sales: float, observed_sales: float, *, tolerance: float = 0.01) -> ReconciliationResult:
    if tolerance < 0:
        raise ValueError("tolerance must be non-negative")
    delta = float(observed_sales) - float(expected_sales)
    return ReconciliationResult(
        expected_sales=float(expected_sales),
        observed_sales=float(observed_sales),
        delta=delta,
        balanced=isclose(float(expected_sales), float(observed_sales), abs_tol=tolerance),
    )
