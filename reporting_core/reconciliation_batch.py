"""Batch-level summaries for deterministic report reconciliation."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
from reporting_core.reconciliation import ReconciliationResult

@dataclass(frozen=True)
class ReconciliationBatchSummary:
    count: int
    balanced: int
    unbalanced: int
    total_absolute_delta: float

def summarize_reconciliations(results: Iterable[ReconciliationResult]) -> ReconciliationBatchSummary:
    items = list(results)
    return ReconciliationBatchSummary(len(items), sum(r.balanced for r in items), sum(not r.balanced for r in items), round(sum(abs(r.delta) for r in items), 2))
