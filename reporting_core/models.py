from dataclasses import dataclass
from typing import Literal

Status = Literal["Active", "No Movement"]


@dataclass(frozen=True)
class ReportRow:
    site: str
    category: str
    product: str
    quantity: float
    sales: float
    status: Status


@dataclass(frozen=True)
class ReportSummary:
    total_sales: float
    total_quantity: float
    active_products: int
    no_movement_products: int

    @property
    def product_count(self) -> int:
        return self.active_products + self.no_movement_products
