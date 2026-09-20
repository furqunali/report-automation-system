"""Data-quality metrics for monthly report runs."""
from __future__ import annotations
from dataclasses import dataclass
from .models import ReportRow

@dataclass(frozen=True)
class QualityReport:
    rows: int
    sites: int
    products: int
    invalid_rows: int
    total_sales: float

    @property
    def healthy(self) -> bool:
        return self.rows > 0 and self.invalid_rows == 0

def profile_rows(rows: list[ReportRow]) -> QualityReport:
    invalid = 0
    valid = []
    for row in rows:
        try:
            from .validation import validate_row
            validate_row(row)
            valid.append(row)
        except ValueError:
            invalid += 1
    return QualityReport(
        rows=len(rows),
        sites=len({r.site for r in valid}),
        products=len({r.product for r in valid}),
        invalid_rows=invalid,
        total_sales=round(sum(r.sales for r in valid), 2),
    )
