from __future__ import annotations

import pandas as pd


def fmt_num(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    try:
        return f"{float(value):,.2f}"
    except (TypeError, ValueError):
        return ""


def fmt_currency(value: object, currency: str = "MXN") -> str:
    formatted = fmt_num(value)
    if not formatted:
        return ""
    currency_label = (currency or "MXN").upper()
    prefix = "$" if currency_label == "MXN" else currency_label
    return f"{prefix} {formatted}"


def fmt_int(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    try:
        return f"{int(round(float(value))):,}"
    except (TypeError, ValueError):
        return ""


def fmt_percent(value: object) -> str:
    formatted = fmt_num(value)
    if not formatted:
        return ""
    return f"{formatted}%"
