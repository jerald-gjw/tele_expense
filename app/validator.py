from __future__ import annotations

from decimal import Decimal, InvalidOperation


class InputValidationError(ValueError):
    pass


def parse_expense_text(text: str) -> tuple[str, str, float]:
    parts = text.strip().split()
    if len(parts) < 3:
        raise InputValidationError("Invalid format")

    expense_type = parts[0]
    price_text = parts[-1]
    name = " ".join(parts[1:-1]).strip().lower()

    if not expense_type or not name:
        raise InputValidationError("Invalid format")

    try:
        value = Decimal(price_text)
    except InvalidOperation as exc:
        raise InputValidationError("Invalid price") from exc

    if value <= 0:
        raise InputValidationError("Invalid price")

    quantized = value.quantize(Decimal("0.01"))
    return expense_type, name, float(quantized)
