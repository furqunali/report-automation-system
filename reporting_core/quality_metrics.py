"""Quality metrics and deterministic validation summaries for report runs."""
from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class QualityMetric:
    name: str
    value: float
    threshold: float
    passed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

def _number(value: Any, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not math.isfinite(result):
        raise ValueError(f"{field} must be finite")
    return result

def completeness_rate(total: Any, completed: Any) -> float:
    total_n = _number(total, "total")
    completed_n = _number(completed, "completed")
    if total_n < 0 or completed_n < 0:
        raise ValueError("counts must be non-negative")
    if completed_n > total_n:
        raise ValueError("completed cannot exceed total")
    return completed_n / total_n if total_n else 1.0

def accuracy_rate(correct: Any, total: Any) -> float:
    return completeness_rate(total, correct)

def metric(name: str, value: Any, threshold: Any, *, minimum: bool = True) -> QualityMetric:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("metric name must be non-empty")
    value_n, threshold_n = _number(value, "value"), _number(threshold, "threshold")
    passed = value_n >= threshold_n if minimum else value_n <= threshold_n
    return QualityMetric(name.strip(), value_n, threshold_n, passed)

def summarize(metrics: Iterable[QualityMetric]) -> dict[str, Any]:
    values = list(metrics)
    if not all(isinstance(item, QualityMetric) for item in values):
        raise TypeError("metrics must contain QualityMetric values")
    passed = sum(item.passed for item in values)
    return {
        "total": len(values),
        "passed": passed,
        "failed": len(values) - passed,
        "pass_rate": passed / len(values) if values else 1.0,
        "metrics": [item.to_dict() for item in values],
    }

def build_quality_report(records: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    rows = list(records)
    total = len(rows)
    complete = sum(bool(row.get("complete")) for row in rows)
    valid = sum(bool(row.get("valid")) for row in rows)
    metrics = [
        metric("completeness", completeness_rate(total, complete), 0.95),
        metric("validity", accuracy_rate(valid, total), 0.99),
    ]
    return summarize(metrics)
