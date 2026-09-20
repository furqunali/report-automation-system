"""Detect exact duplicate report rows before aggregation."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from .models import ReportRow


def duplicate_row_indices(rows: Iterable[ReportRow]) -> dict[tuple[str, str, str, float, float, str], list[int]]:
    """Return duplicate row positions grouped by their exact row identity."""
    groups: defaultdict[tuple[str, str, str, float, float, str], list[int]] = defaultdict(list)
    for index, row in enumerate(rows):
        key = (row.site, row.category, row.product, row.quantity, row.sales, row.status)
        groups[key].append(index)
    return {key: indices for key, indices in groups.items() if len(indices) > 1}
