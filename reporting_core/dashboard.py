"""Deterministic ``dashboard/data.js`` generation from processed report rows.

The static dashboard (``dashboard/dashboard.html``) reads a single global,
``window.REPORT_DATA``, shaped as::

    {"summary": {...}, "records": [{"Site": ..., "Category": ..., ...}, ...]}

This module turns processed report rows plus a run timestamp into exactly that
contract and renders it as the ``data.js`` file the dashboard loads over
``file://``.  Output is byte-for-byte deterministic for a given input (stable
key order, stable float rounding), so re-runs are reproducible and diffs stay
readable.

Keeping this here (rather than inline in ``process_reports.py``) makes the
dashboard payload a first-class, independently testable contract: the same
logic powers both the CLI and any future caller.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

RECORD_FIELDS: tuple[str, ...] = (
    "Site", "Category", "Product", "Quantity", "Sales", "Status",
)

NO_MOVEMENT_STATUSES = frozenset({"no movement", "inactive"})

Record = Mapping[str, Any]


def coerce_number(value: Any) -> float:
    """Parse a messy sales/quantity cell into a finite float."""
    if isinstance(value, bool):
        return 0.0
    text = str(value).replace(",", "").replace("$", "").strip()
    if not text:
        return 0.0
    if text.startswith("(") and text.endswith(")"):
        text = "-" + text[1:-1].strip()
    try:
        number = float(text)
    except ValueError:
        return 0.0
    return number if math.isfinite(number) else 0.0


def is_no_movement(status: Any) -> bool:
    """Return True when ``status`` marks a product as not moving."""
    return str(status).strip().lower() in NO_MOVEMENT_STATUSES


@dataclass(frozen=True)
class DashboardSummary:
    processing_date: str
    total_records: int
    total_sales: float
    total_quantity: float
    active_products: int
    no_movement: int
    master_file: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "processing_date": self.processing_date,
            "total_records": self.total_records,
            "total_sales": self.total_sales,
            "total_quantity": self.total_quantity,
            "active_products": self.active_products,
            "no_movement": self.no_movement,
            "master_file": self.master_file,
        }


def build_summary(
    records: Sequence[Record],
    processing_date: str,
    master_file: str = "",
) -> DashboardSummary:
    total_sales = sum(coerce_number(r.get("Sales")) for r in records)
    total_quantity = sum(coerce_number(r.get("Quantity")) for r in records)
    no_movement = sum(1 for r in records if is_no_movement(r.get("Status")))
    return DashboardSummary(
        processing_date=processing_date,
        total_records=len(records),
        total_sales=round(total_sales, 2),
        total_quantity=round(total_quantity, 2),
        active_products=len(records) - no_movement,
        no_movement=no_movement,
        master_file=master_file,
    )


def normalize_record(record: Record) -> dict[str, Any]:
    ordered: dict[str, Any] = {field: record.get(field, "") for field in RECORD_FIELDS}
    for key, value in record.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def build_dashboard_payload(
    records: Sequence[Record],
    processing_date: str,
    master_file: str = "",
) -> dict[str, Any]:
    summary = build_summary(records, processing_date, master_file)
    return {
        "summary": summary.as_dict(),
        "records": [normalize_record(r) for r in records],
    }


def render_data_js(payload: Mapping[str, Any]) -> str:
    body = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"window.REPORT_DATA = {body};\n"


def write_data_js(payload: Mapping[str, Any], path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render_data_js(payload), encoding="utf-8")
    return target


def generate_data_js(
    records: Sequence[Record],
    path: str | Path,
    processing_date: str,
    master_file: str = "",
) -> Path:
    payload = build_dashboard_payload(records, processing_date, master_file)
    return write_data_js(payload, path)
