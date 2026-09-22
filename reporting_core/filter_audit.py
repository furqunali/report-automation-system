"""Canonical filter representation for report audit logs."""
from __future__ import annotations

from reporting_core.filter_contract import FilterContract


def canonical_filter_key(filters: FilterContract) -> str:
    normalized=filters.normalized()
    parts=[]
    for name,value in (("site",normalized.site),("category",normalized.category),("product",normalized.product)):
        if value is not None:
            parts.append(f"{name}={value}")
    return ";".join(parts)
