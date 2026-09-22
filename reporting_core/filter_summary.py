"""Deterministic summary for active dashboard filters."""
from __future__ import annotations

from reporting_core.filter_contract import FilterContract


def summarize_filters(filters: FilterContract) -> dict[str, str]:
    normalized = filters.normalized()
    return {key: value for key, value in (("site", normalized.site), ("category", normalized.category), ("product", normalized.product)) if value is not None}
