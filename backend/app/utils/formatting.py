"""Locale-aware money formatting (ADR-007)."""

from __future__ import annotations


def format_money(
    cents: int,
    *,
    currency_code: str = "ALL",
    locale: str = "sq-AL",
) -> str:
    """Format integer minor units for API display fields."""
    amount = cents / 100

    if currency_code == "ALL" and locale.startswith("sq"):
        if amount == int(amount):
            grouped = f"{int(amount):,}".replace(",", ".")
            return f"{grouped} Lek"
        whole = f"{amount:,.2f}"
        parts = whole.split(".")
        int_part = parts[0].replace(",", ".")
        dec_part = parts[1] if len(parts) > 1 else "00"
        return f"{int_part},{dec_part} Lek"

    symbols = {"EUR": "€", "USD": "$", "GBP": "£"}
    if currency_code in symbols:
        return f"{symbols[currency_code]}{amount:,.2f}"

    return f"{currency_code} {amount:,.2f}"
