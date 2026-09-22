"""Schema validation for exported reconciliation health reports."""
from __future__ import annotations
REQUIRED_FIELDS = frozenset({"count","balanced","unbalanced","balanced_ratio"})
def validate_reconciliation_report(payload: dict) -> bool:
    if not isinstance(payload, dict) or set(payload) != REQUIRED_FIELDS: return False
    if not all(type(payload[name]) is int and payload[name] >= 0 for name in ("count","balanced","unbalanced")): return False
    ratio = payload["balanced_ratio"]
    return type(ratio) in (int,float) and 0 <= ratio <= 1 and payload["balanced"] + payload["unbalanced"] == payload["count"]
