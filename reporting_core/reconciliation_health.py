"""Deterministic health summary for reconciliation batches."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
from reporting_core.reconciliation import ReconciliationResult

@dataclass(frozen=True)
class ReconciliationHealth:
    count: int
    balanced: int
    unbalanced: int
    balanced_ratio: float

def summarize_reconciliation_health(results: Iterable[ReconciliationResult]) -> ReconciliationHealth:
    items = list(results)
    balanced = sum(item.balanced for item in items)
    count = len(items)
    return ReconciliationHealth(count, balanced, count - balanced, round(balanced / count, 4) if count else 0.0)
