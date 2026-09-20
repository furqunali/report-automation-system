"""Validated export contract for report and dashboard handoff."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class ExportContract:
    schema_version: str
    rows: tuple[dict[str, Any], ...]
    total_sales: float
    row_count: int

    def __post_init__(self) -> None:
        if not self.schema_version.strip():
            raise ValueError("schema_version is required")
        if self.row_count != len(self.rows):
            raise ValueError("row_count must match rows")
        if self.total_sales < 0:
            raise ValueError("total_sales must be non-negative")

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "row_count": self.row_count,
            "total_sales": round(self.total_sales, 2),
            "rows": [dict(row) for row in self.rows],
        }

def build_export_contract(rows: list[dict[str, Any]], total_sales: float, schema_version: str = "1") -> ExportContract:
    if not all(isinstance(row, dict) for row in rows):
        raise TypeError("rows must contain dictionaries")
    return ExportContract(schema_version, tuple(dict(row) for row in rows), float(total_sales), len(rows))
