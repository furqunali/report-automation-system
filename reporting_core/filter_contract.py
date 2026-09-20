"""Validated dashboard filter contract."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class FilterContract:
    site: str | None = None
    category: str | None = None
    product: str | None = None

    def normalized(self) -> "FilterContract":
        clean=lambda value: value.strip() if isinstance(value,str) and value.strip() else None
        return FilterContract(clean(self.site),clean(self.category),clean(self.product))

def matches_filters(row: object, filters: FilterContract) -> bool:
    active=filters.normalized()
    return all(
        expected is None or getattr(row, field, None) == expected
        for field, expected in (("site",active.site),("category",active.category),("product",active.product))
    )
