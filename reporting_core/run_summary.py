"""Summarize an automation run for logs and dashboard handoff."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RunSummary:
    rows_received: int
    rows_valid: int
    rows_invalid: int
    total_sales: float
    successful: bool

def build_run_summary(rows_received: int, rows_valid: int, rows_invalid: int, total_sales: float) -> RunSummary:
    if min(rows_received, rows_valid, rows_invalid) < 0:
        raise ValueError("row counts must be non-negative")
    if rows_valid + rows_invalid != rows_received:
        raise ValueError("valid and invalid rows must equal received rows")
    if total_sales < 0:
        raise ValueError("total_sales must be non-negative")
    return RunSummary(rows_received, rows_valid, rows_invalid, round(total_sales, 2),
                      rows_invalid == 0)
