from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ExpenseEntry:
    expense_type: str
    name: str
    price: float
    created_at: datetime

    def to_sheet_row(self) -> list[str]:
        return [
            self.created_at.strftime("%Y-%m-%d"),
            self.created_at.strftime("%H:%M:%S"),
            self.expense_type,
            self.name,
            f"{self.price:.2f}",
        ]
