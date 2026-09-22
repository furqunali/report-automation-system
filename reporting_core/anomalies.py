"""Detect data anomalies before KPI aggregation."""
from __future__ import annotations

from dataclasses import dataclass

from reporting_core.models import ReportRow


@dataclass(frozen=True)
class Anomaly:
    row_index: int
    code: str
    message: str


def find_anomalies(rows: list[ReportRow]) -> list[Anomaly]:
    """Return deterministic validation anomalies without mutating input rows."""
    anomalies: list[Anomaly] = []
    for index, row in enumerate(rows):
        if row.quantity < 0:
            anomalies.append(Anomaly(index, "negative_quantity", "quantity must be non-negative"))
        if row.sales < 0:
            anomalies.append(Anomaly(index, "negative_sales", "sales must be non-negative"))
        if row.status not in ("Active", "No Movement"):
            anomalies.append(Anomaly(index, "invalid_status", "status is not recognized"))
    return anomalies
