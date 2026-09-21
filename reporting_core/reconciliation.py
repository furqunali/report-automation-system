"""Deterministic reconciliation checks for report totals."""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose, isfinite
from numbers import Real


@dataclass(frozen=True)
class ReconciliationResult:
    expected_sales: float
    observed_sales: float
    delta: float
    balanced: bool


def reconcile_sales(expected_sales: float, observed_sales: float, *, tolerance: float = 0.01) -> ReconciliationResult:
    if not isinstance(expected_sales, Real) or not isinstance(observed_sales, Real):
        raise TypeError("sales values must be numeric")
    if not isinstance(tolerance, Real) or isinstance(tolerance, bool):
        raise TypeError("tolerance must be numeric")
    tolerance = float(tolerance)
    if not isfinite(tolerance) or tolerance < 0:
        raise ValueError("tolerance must be a finite non-negative number")
    expected = float(expected_sales)
    observed = float(observed_sales)
    if not isfinite(expected) or not isfinite(observed):
        raise ValueError("sales values must be finite")
    delta = observed - expected
    return ReconciliationResult(
        expected_sales=expected,
        observed_sales=observed,
        delta=delta,
        balanced=isclose(expected, observed, rel_tol=0.0, abs_tol=tolerance),
    )
