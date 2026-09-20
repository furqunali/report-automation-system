"""Policy findings derived from report run health."""
from __future__ import annotations
from dataclasses import dataclass
from reporting_core.run_health import RunHealth

@dataclass(frozen=True)
class RunFinding:
    code: str
    severity: str
    message: str

def evaluate_run(health: RunHealth) -> tuple[RunFinding, ...]:
    findings: list[RunFinding] = []
    if health.status == "empty":
        findings.append(RunFinding("EMPTY_RUN", "warning", "run received no rows"))
    if health.error_rate > 0:
        findings.append(RunFinding("INVALID_ROWS", "error", f"invalid row rate is {health.error_rate:.4f}"))
    if health.status == "healthy" and not findings:
        findings.append(RunFinding("HEALTHY", "info", "report run passed all health checks"))
    return tuple(findings)
