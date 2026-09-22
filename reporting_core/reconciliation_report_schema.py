"""Schema validation for exported reconciliation health reports."""
from __future__ import annotations
REQUIRED_FIELDS = frozenset({"count","balanced","unbalanced","balanced_ratio"})
def validate_reconciliation_report(payload: dict) -> bool:
    if not isinstance(payload, dict) or set(payload) != REQUIRED_FIELDS: return False
    if not all(type(payload[name]) is int and payload[name] >= 0 for name in ("count","balanced","unbalanced")): return False
    if payload["balanced"] + payload["unbalanced"] != payload["count"]: return False
    ratio = payload["balanced_ratio"]
    if type(ratio) not in (int,float) or not 0 <= ratio <= 1: return False
    expected = payload["balanced"] / payload["count"] if payload["count"] else 0
    return ratio == expected
