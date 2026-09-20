"""Deterministic health classification for report automation runs."""
from __future__ import annotations
from dataclasses import dataclass
from reporting_core.run_summary import RunSummary

@dataclass(frozen=True)
class RunHealth:
    status: str
    valid_rate: float
    error_rate: float
    actionable: bool

def assess_run(summary: RunSummary) -> RunHealth:
    total = summary.rows_received
    if total == 0:
        return RunHealth("empty", 0.0, 0.0, True)
    valid_rate = round(summary.rows_valid / total, 4)
    error_rate = round(summary.rows_invalid / total, 4)
    status = "healthy" if summary.successful else "degraded"
    return RunHealth(status, valid_rate, error_rate, not summary.successful)
