"""Deterministic direction counts for reconciliation deltas."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from reporting_core.reconciliation import ReconciliationResult


@dataclass(frozen=True)
class ReconciliationDirectionSummary:
    count: int
    positive: int
    negative: int
    zero: int

def summarize_reconciliation_direction(results: Iterable[ReconciliationResult]) -> ReconciliationDirectionSummary:
    items=list(results)
    positive=sum(r.delta > 0 for r in items)
    negative=sum(r.delta < 0 for r in items)
    return ReconciliationDirectionSummary(len(items),positive,negative,len(items)-positive-negative)
