"""Batch-level summaries for deterministic report reconciliation."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from reporting_core.reconciliation import ReconciliationResult


@dataclass(frozen=True)
class ReconciliationBatchSummary:
    count: int
    balanced: int
    unbalanced: int
    total_absolute_delta: float
    balanced_rate: float
    maximum_absolute_delta: float

def summarize_reconciliations(results: Iterable[ReconciliationResult]) -> ReconciliationBatchSummary:
    items = list(results)
    absolute_deltas = [abs(r.delta) for r in items]
    balanced = sum(r.balanced for r in items)
    return ReconciliationBatchSummary(len(items), balanced, len(items) - balanced, round(sum(absolute_deltas), 2), round(balanced / len(items), 4) if items else 0.0, round(max(absolute_deltas), 2) if items else 0.0)
