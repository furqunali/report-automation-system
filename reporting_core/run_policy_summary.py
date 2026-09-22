"""Aggregate deterministic report run policy findings."""
from __future__ import annotations

from dataclasses import dataclass

from reporting_core.run_policy import RunFinding


@dataclass(frozen=True)
class RunPolicySummary:
    total: int
    errors: int
    warnings: int
    infos: int
    healthy: bool

def summarize_run(findings: tuple[RunFinding, ...]) -> RunPolicySummary:
    errors = sum(f.severity == "error" for f in findings)
    warnings = sum(f.severity == "warning" for f in findings)
    infos = sum(f.severity == "info" for f in findings)
    return RunPolicySummary(len(findings), errors, warnings, infos, errors == 0)
