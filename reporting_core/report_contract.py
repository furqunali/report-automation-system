"""Stable contract for serialized report summaries."""
from __future__ import annotations

REQUIRED_FIELDS = ("expected_sales", "observed_sales", "delta", "balanced")

def validate_reconciliation_payload(payload: dict) -> bool:
    if not isinstance(payload, dict):
        raise TypeError("payload must be a dict")
    missing = [field for field in REQUIRED_FIELDS if field not in payload]
    if missing:
        raise ValueError("missing fields: " + ", ".join(missing))
    if not isinstance(payload["balanced"], bool):
        raise TypeError("balanced must be boolean")
    return True
