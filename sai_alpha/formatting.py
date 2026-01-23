from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st


DEFAULT_TEXT = "N/D"


def _to_float(value: Any) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)) or pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def fmt_num(value: Any, default: str = DEFAULT_TEXT) -> str:
    number = _to_float(value)
    if number is None:
        return default
    return f"{number:,.2f}"


def fmt_money(value: Any, currency: str = "MXN", default: str = DEFAULT_TEXT) -> str:
    formatted = fmt_num(value, default=default)
    if formatted == default:
        return default
    currency_label = (currency or "MXN").upper()
    prefix = "$" if currency_label == "MXN" else currency_label
    return f"{prefix} {formatted}"


def fmt_int(value: Any, default: str = DEFAULT_TEXT) -> str:
    number = _to_float(value)
    if number is None:
        return default
    return f"{int(round(number)):,.0f}"


def safe_metric(label: str, value: Any, delta: Any | None = None, help: str | None = None) -> None:
    if isinstance(value, str):
        display_value = value
    else:
        display_value = fmt_num(value)
    if delta is None:
        st.metric(label, display_value, help=help)
        return
    if isinstance(delta, str):
        display_delta = delta
    else:
        display_delta = fmt_num(delta)
    st.metric(label, display_value, delta=display_delta, help=help)
