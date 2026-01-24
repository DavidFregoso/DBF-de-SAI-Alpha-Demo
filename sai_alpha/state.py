from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd
import streamlit as st


@dataclass
class LatestPeriods:
    min_date: date
    max_date: date
    latest_day: date
    latest_week_year: int
    latest_week: int
    latest_month_year: int
    latest_month: int
    latest_year: int
    years: list[int]
    weeks_by_year: dict[int, list[int]]
    months_by_year: dict[int, list[int]]


def compute_latest_periods(df_sales: pd.DataFrame) -> LatestPeriods:
    if df_sales.empty or "SALE_DATE" not in df_sales.columns:
        today = date.today()
        iso = today.isocalendar()
        return LatestPeriods(
            min_date=today,
            max_date=today,
            latest_day=today,
            latest_week_year=int(iso.year),
            latest_week=int(iso.week),
            latest_month_year=int(today.year),
            latest_month=int(today.month),
            latest_year=int(today.year),
            years=[int(today.year)],
            weeks_by_year={int(today.year): [int(iso.week)]},
            months_by_year={int(today.year): [int(today.month)]},
        )
    sales_dates = pd.to_datetime(df_sales["SALE_DATE"]).dropna()
    min_date = sales_dates.min().date()
    max_date = sales_dates.max().date()
    iso = sales_dates.dt.isocalendar()
    weeks_by_year = (
        pd.DataFrame({"year": iso.year, "week": iso.week})
        .drop_duplicates()
        .groupby("year")["week"]
        .apply(lambda series: sorted(series.astype(int).unique().tolist()))
        .to_dict()
    )
    months_by_year = (
        pd.DataFrame({"year": sales_dates.dt.year, "month": sales_dates.dt.month})
        .drop_duplicates()
        .groupby("year")["month"]
        .apply(lambda series: sorted(series.astype(int).unique().tolist()))
        .to_dict()
    )
    latest_iso = max_date.isocalendar()
    return LatestPeriods(
        min_date=min_date,
        max_date=max_date,
        latest_day=max_date,
        latest_week_year=int(latest_iso.year),
        latest_week=int(latest_iso.week),
        latest_month_year=int(max_date.year),
        latest_month=int(max_date.month),
        latest_year=int(max_date.year),
        years=sorted(sales_dates.dt.year.unique().tolist()),
        weeks_by_year=weeks_by_year,
        months_by_year=months_by_year,
    )


def init_state_once(df_sales: pd.DataFrame) -> None:
    if st.session_state.get("state_initialized"):
        return

    latest = compute_latest_periods(df_sales)
    st.session_state["latest_periods"] = latest
    st.session_state["data_min_date"] = latest.min_date
    st.session_state["data_max_date"] = latest.max_date

    defaults = {
        "theme_primary": "#0f5132",
        "theme_accent": "#198754",
        "table_density": "Confortable",
        "theme": "Claro",
        "default_window_days": 90,
        "period_type": "Último periodo disponible (recomendado)",
        "granularity": "Auto",
        "currency_view": "MXN",
        "selected_week_year": latest.latest_week_year,
        "selected_week": latest.latest_week,
        "selected_month_year": latest.latest_month_year,
        "selected_month": latest.latest_month,
        "selected_year": latest.latest_year,
        "range_start": latest.min_date,
        "range_end": latest.max_date,
        "last_valid_range": (latest.min_date, latest.max_date),
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)

    st.session_state["state_initialized"] = True


def get_filters() -> dict[str, object]:
    return {
        "period_type": st.session_state.get("period_type"),
        "granularity": st.session_state.get("granularity"),
        "currency_view": st.session_state.get("currency_view"),
        "selected_week_year": st.session_state.get("selected_week_year"),
        "selected_week": st.session_state.get("selected_week"),
        "selected_month_year": st.session_state.get("selected_month_year"),
        "selected_month": st.session_state.get("selected_month"),
        "selected_year": st.session_state.get("selected_year"),
        "range_start": st.session_state.get("range_start"),
        "range_end": st.session_state.get("range_end"),
        "brands": st.session_state.get("filter_brands"),
        "categories": st.session_state.get("filter_categories"),
        "vendors": st.session_state.get("filter_vendors"),
        "sale_origins": st.session_state.get("filter_sale_origins"),
        "client_origins": st.session_state.get("filter_client_origins"),
        "recommendation_sources": st.session_state.get("filter_recommendations"),
        "invoice_types": st.session_state.get("filter_invoice_types"),
        "order_types": st.session_state.get("filter_order_types"),
        "order_statuses": st.session_state.get("filter_order_statuses"),
    }


def set_filter(key: str, value: object) -> None:
    st.session_state[key] = value
