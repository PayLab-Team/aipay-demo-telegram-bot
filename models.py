from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class InvoiceStatus(Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"


@dataclass
class MenuItem:
    id: int
    name: str
    price: int  # in tenge


@dataclass
class Order:
    user_id: int
    items: list[MenuItem] = field(default_factory=list)
    phone: Optional[str] = None
    invoice_id: Optional[str] = None

    @property
    def total(self) -> int:
        return sum(item.price for item in self.items)

    @property
    def is_empty(self) -> bool:
        return len(self.items) == 0

    def add_item(self, item: MenuItem) -> None:
        self.items.append(item)

    def clear(self) -> None:
        self.items.clear()
        self.phone = None
        self.invoice_id = None


# Demo menu items (low prices for demo/testing)
MENU_ITEMS = [
    MenuItem(id=1, name="Американо", price=10),
    MenuItem(id=2, name="Бургер", price=25),
    MenuItem(id=3, name="Пицца", price=50),
    MenuItem(id=4, name="Салат", price=35),
    MenuItem(id=5, name="Десерт", price=100),
]


def get_menu_item_by_id(item_id: int) -> Optional[MenuItem]:
    for item in MENU_ITEMS:
        if item.id == item_id:
            return item
    return None
