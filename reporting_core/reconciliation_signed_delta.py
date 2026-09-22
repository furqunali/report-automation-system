"""Signed-delta summaries for reconciliation batches."""
from __future__ import annotations

from collections.abc import Iterable

from reporting_core.reconciliation import ReconciliationResult


def mean_signed_delta(results: Iterable[ReconciliationResult]) -> float:
    deltas = [float(result.delta) for result in results]
    return round(sum(deltas) / len(deltas), 2) if deltas else 0.0
