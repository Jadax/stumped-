"""Display-only multi-currency support.

The simulation stores all money in integer GBP base units so changing a display
preference can never alter budgets or introduce rounding loss.  Conversion
rates are a fixed game-balancing table, not a live foreign-exchange service.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


CURRENCIES = {
    "GBP": {"symbol": "£", "name": "British Pound", "rate": Decimal("1.00")},
    "USD": {"symbol": "$", "name": "US Dollar", "rate": Decimal("1.30")},
    "EUR": {"symbol": "€", "name": "Euro", "rate": Decimal("1.15")},
    "AUD": {"symbol": "A$", "name": "Australian Dollar", "rate": Decimal("1.90")},
    "INR": {"symbol": "₹", "name": "Indian Rupee", "rate": Decimal("105.00")},
    "ZAR": {"symbol": "R", "name": "South African Rand", "rate": Decimal("18.50")},
    "NZD": {"symbol": "NZ$", "name": "New Zealand Dollar", "rate": Decimal("2.10")},
    "PKR": {"symbol": "₨", "name": "Pakistani Rupee", "rate": Decimal("280.00")},
    "LKR": {"symbol": "Rs", "name": "Sri Lankan Rupee", "rate": Decimal("380.00")},
    "BDT": {"symbol": "৳", "name": "Bangladeshi Taka", "rate": Decimal("140.00")},
}

_active_currency = "GBP"


def set_active_currency(code: str) -> str:
    global _active_currency
    _active_currency = code if code in CURRENCIES else "GBP"
    return _active_currency


def get_active_currency() -> str:
    return _active_currency


def convert_from_gbp(amount: int | float | Decimal, code: str | None = None) -> Decimal:
    selected = code or _active_currency
    selected = selected if selected in CURRENCIES else "GBP"
    return (Decimal(str(amount)) * CURRENCIES[selected]["rate"]).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def format_money(amount: int | float | Decimal, code: str | None = None, *, compact: bool = False) -> str:
    selected = code or _active_currency
    selected = selected if selected in CURRENCIES else "GBP"
    value = convert_from_gbp(amount, selected)
    symbol = CURRENCIES[selected]["symbol"]
    sign = "-" if value < 0 else ""
    absolute = abs(value)
    if compact:
        if absolute >= 1_000_000_000:
            return f"{sign}{symbol}{float(absolute / Decimal('1000000000')):.1f}B"
        if absolute >= 1_000_000:
            return f"{sign}{symbol}{float(absolute / Decimal('1000000')):.1f}M"
        if absolute >= 1_000:
            return f"{sign}{symbol}{float(absolute / Decimal('1000')):.1f}K"
    return f"{sign}{symbol}{int(absolute):,}"


def currency_options() -> list[str]:
    return list(CURRENCIES)
