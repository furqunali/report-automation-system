"""Decision-ready quality metrics for report automation handoff."""
from __future__ import annotations

from dataclasses import dataclass
from .quality import QualityReport


@dataclass(frozen=True)
class QualitySummary:
    valid_rate: float
    invalid_rate: float
    has_data: bool
    ready_for_export: bool


def summarize_quality(report: QualityReport) -> QualitySummary:
    """Convert a quality report into stable rates and an export gate."""
    if report.rows < 0 or report.invalid_rows < 0:
        raise ValueError("row counts must be non-negative")
    if report.invalid_rows > report.rows:
        raise ValueError("invalid rows cannot exceed total rows")
    if report.rows == 0:
        return QualitySummary(0.0, 0.0, False, False)
    valid_rate = round((report.rows - report.invalid_rows) / report.rows, 4)
    invalid_rate = round(report.invalid_rows / report.rows, 4)
    return QualitySummary(
        valid_rate=valid_rate,
        invalid_rate=invalid_rate,
        has_data=True,
        ready_for_export=report.healthy,
    )
