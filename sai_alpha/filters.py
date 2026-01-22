from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import calendar

import pandas as pd
import streamlit as st

from sai_alpha.state import LatestPeriods
from sai_alpha.ui import normalize_currency, validate_sales_schema


@dataclass
class FilterState:
    start_date: date
    end_date: date
    granularity: str
    currency_mode: str
    brands: list[str]
    categories: list[str]
    vendors: list[str]
    sale_origins: list[str]
    client_origins: list[str]
    recommendation_sources: list[str]
    invoice_types: list[str]
    order_types: list[str]
    order_statuses: list[str] | None
    sales: pd.DataFrame
    pedidos: pd.DataFrame | None
    currency_label: str
    revenue_column: str
    unit_price_column: str
    fx_average: float | None


def _init_multiselect_state(key: str, options: list[str]) -> None:
    if key not in st.session_state:
        st.session_state[key] = options
        return
    current = st.session_state[key]
    if not current:
        return
    st.session_state[key] = [value for value in current if value in options]


def multiselect_with_actions(label: str, options: list[str], key: str) -> list[str]:
    _init_multiselect_state(key, options)
    col1, col2 = st.sidebar.columns(2)
    if col1.button("Seleccionar todo", key=f"{key}_all"):
        st.session_state[key] = options
    if col2.button("Limpiar", key=f"{key}_clear"):
        st.session_state[key] = []
    return st.sidebar.multiselect(label, options, key=key)


def _week_range_from_selection(year: int, week: int) -> tuple[date, date]:
    start = date.fromisocalendar(year, week, 1)
    end = date.fromisocalendar(year, week, 7)
    return start, end


def _month_range_from_selection(year: int, month: int) -> tuple[date, date]:
    start = date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end = date(year, month, last_day)
    return start, end


def _year_range_from_selection(year: int) -> tuple[date, date]:
    return date(year, 1, 1), date(year, 12, 31)


def _sync_period_on_granularity(latest: LatestPeriods, granularity: str) -> None:
    prev = st.session_state.get("granularity_prev", granularity)
    if prev == granularity:
        return
    if granularity == "Diario":
        st.session_state["period_day"] = latest.latest_day
    elif granularity == "Semanal":
        st.session_state["period_week_year"] = latest.latest_week_year
        st.session_state["period_week"] = latest.latest_week
    elif granularity == "Mensual":
        st.session_state["period_month_year"] = latest.latest_month_year
        st.session_state["period_month"] = latest.latest_month
    else:
        st.session_state["period_year"] = latest.latest_year
    st.session_state["granularity_prev"] = granularity


def _resolve_period_range(latest: LatestPeriods, granularity: str) -> tuple[date, date]:
    if granularity == "Diario":
        period_day = st.session_state.get("period_day", latest.latest_day)
        if period_day < latest.min_date or period_day > latest.max_date:
            st.session_state["period_day"] = latest.latest_day
        period_day = st.sidebar.date_input(
            "Día",
            key="period_day",
            min_value=latest.min_date,
            max_value=latest.max_date,
        )
        return period_day, period_day
    if granularity == "Semanal":
        if st.session_state.get("period_week_year") not in latest.years:
            st.session_state["period_week_year"] = latest.latest_week_year
        year = st.sidebar.selectbox(
            "Año",
            latest.years,
            key="period_week_year",
        )
        weeks = latest.weeks_by_year.get(int(year), [])
        if not weeks:
            weeks = [latest.latest_week]
        if st.session_state.get("period_week") not in weeks:
            st.session_state["period_week"] = weeks[-1]
        week = st.sidebar.selectbox("Semana", weeks, key="period_week")
        return _week_range_from_selection(int(year), int(week))
    if granularity == "Mensual":
        if st.session_state.get("period_month_year") not in latest.years:
            st.session_state["period_month_year"] = latest.latest_month_year
        year = st.sidebar.selectbox(
            "Año",
            latest.years,
            key="period_month_year",
        )
        months = latest.months_by_year.get(int(year), [])
        if not months:
            months = [latest.latest_month]
        if st.session_state.get("period_month") not in months:
            st.session_state["period_month"] = months[-1]
        month = st.sidebar.selectbox(
            "Mes",
            months,
            format_func=lambda value: calendar.month_name[int(value)],
            key="period_month",
        )
        return _month_range_from_selection(int(year), int(month))
    if st.session_state.get("period_year") not in latest.years:
        st.session_state["period_year"] = latest.latest_year
    year = st.sidebar.selectbox("Año", latest.years, key="period_year")
    return _year_range_from_selection(int(year))


def render_sidebar_filters(ventas: pd.DataFrame, pedidos: pd.DataFrame | None) -> FilterState:
    latest: LatestPeriods = st.session_state["latest_periods"]
    st.sidebar.caption("Filtros globales")

    granularity = st.sidebar.selectbox(
        "Granularidad",
        ["Diario", "Semanal", "Mensual", "Anual"],
        key="granularity",
    )
    _sync_period_on_granularity(latest, granularity)

    st.sidebar.markdown("**Periodo**")
    start_date, end_date = _resolve_period_range(latest, granularity)

    currency_mode = st.sidebar.selectbox(
        "Moneda",
        ["MXN", "USD"],
        key="currency_mode",
    )

    missing_columns = validate_sales_schema(ventas)
    if missing_columns:
        st.sidebar.error(
            "Faltan columnas requeridas en la tabla de ventas: " + ", ".join(missing_columns)
        )
        st.stop()

    brand_options = sorted(ventas["BRAND"].dropna().unique().tolist())
    category_options = sorted(ventas["CATEGORY"].dropna().unique().tolist())
    vendor_options = sorted(ventas["SELLER_NAME"].dropna().unique().tolist())
    sale_origin_options = sorted(ventas["ORIGEN_VENTA"].dropna().unique().tolist())
    client_origin_options = sorted(ventas["CLIENT_ORIGIN"].dropna().unique().tolist())
    recommendation_options = sorted(ventas["RECOMM_SOURCE"].dropna().unique().tolist())
    invoice_options = sorted(ventas["TIPO_FACTURA"].dropna().unique().tolist())
    order_type_options = sorted(ventas["TIPO_ORDEN"].dropna().unique().tolist())

    status_options: list[str] = []
    if pedidos is not None and not pedidos.empty and "STATUS" in pedidos.columns:
        status_options = sorted(pedidos["STATUS"].dropna().unique().tolist())

    st.sidebar.divider()
    brands = multiselect_with_actions("Marca", brand_options, "filter_brands")
    categories = multiselect_with_actions("Categoría", category_options, "filter_categories")
    vendors = multiselect_with_actions("Vendedor", vendor_options, "filter_vendors")
    sale_origins = multiselect_with_actions("Origen de venta", sale_origin_options, "filter_sale_origins")
    client_origins = multiselect_with_actions("Origen de cliente", client_origin_options, "filter_client_origins")
    recommendation_sources = multiselect_with_actions(
        "Recomendación / encuesta",
        recommendation_options,
        "filter_recommendations",
    )
    invoice_types = multiselect_with_actions("Tipo de factura", invoice_options, "filter_invoice_types")
    order_types = multiselect_with_actions("Tipo de orden", order_type_options, "filter_order_types")
    if status_options:
        order_statuses = multiselect_with_actions(
            "Estatus de pedido",
            status_options,
            "filter_order_statuses",
        )
    else:
        order_statuses = None

    ventas_normalized, revenue_column, unit_price_column, currency_label = normalize_currency(
        ventas, currency_mode
    )

    sales_filtered = apply_sales_filters(
        ventas_normalized,
        start_date,
        end_date,
        brands,
        categories,
        vendors,
        sale_origins,
        client_origins,
        recommendation_sources,
        invoice_types,
        order_types,
    )

    pedidos_filtered = None
    if pedidos is not None and not pedidos.empty:
        pedidos_filtered = apply_order_filters(
            pedidos,
            start_date,
            end_date,
            vendors,
            sale_origins,
            order_types,
            order_statuses,
        )

    st.sidebar.caption(f"Registros filtrados: {len(sales_filtered):,}")

    fx_average = None
    if "USD_MXN_RATE" in ventas_normalized.columns:
        fx_filtered = ventas_normalized[
            (ventas_normalized["SALE_DATE"] >= pd.Timestamp(start_date))
            & (ventas_normalized["SALE_DATE"] <= pd.Timestamp(end_date))
        ]
        fx_series = fx_filtered["USD_MXN_RATE"].dropna()
        fx_average = float(fx_series.mean()) if not fx_series.empty else None

    return FilterState(
        start_date=start_date,
        end_date=end_date,
        granularity=granularity,
        currency_mode=currency_mode,
        brands=brands,
        categories=categories,
        vendors=vendors,
        sale_origins=sale_origins,
        client_origins=client_origins,
        recommendation_sources=recommendation_sources,
        invoice_types=invoice_types,
        order_types=order_types,
        order_statuses=order_statuses,
        sales=sales_filtered,
        pedidos=pedidos_filtered,
        currency_label=currency_label,
        revenue_column=revenue_column,
        unit_price_column=unit_price_column,
        fx_average=fx_average,
    )


def apply_sales_filters(
    ventas: pd.DataFrame,
    start_date: date,
    end_date: date,
    brands: list[str],
    categories: list[str],
    vendors: list[str],
    sale_origins: list[str],
    client_origins: list[str],
    recommendation_sources: list[str],
    invoice_types: list[str],
    order_types: list[str],
) -> pd.DataFrame:
    df = ventas.copy()
    df = df[(df["SALE_DATE"] >= pd.Timestamp(start_date)) & (df["SALE_DATE"] <= pd.Timestamp(end_date))]
    if brands:
        df = df[df["BRAND"].isin(brands)]
    else:
        return df.iloc[0:0]
    if categories:
        df = df[df["CATEGORY"].isin(categories)]
    else:
        return df.iloc[0:0]
    if vendors:
        df = df[df["SELLER_NAME"].isin(vendors)]
    else:
        return df.iloc[0:0]
    if sale_origins:
        df = df[df["ORIGEN_VENTA"].isin(sale_origins)]
    else:
        return df.iloc[0:0]
    if client_origins:
        df = df[df["CLIENT_ORIGIN"].isin(client_origins)]
    else:
        return df.iloc[0:0]
    if recommendation_sources:
        df = df[df["RECOMM_SOURCE"].isin(recommendation_sources)]
    else:
        return df.iloc[0:0]
    if invoice_types:
        df = df[df["TIPO_FACTURA"].isin(invoice_types)]
    else:
        return df.iloc[0:0]
    if order_types:
        df = df[df["TIPO_ORDEN"].isin(order_types)]
    else:
        return df.iloc[0:0]
    return df


def apply_order_filters(
    pedidos: pd.DataFrame,
    start_date: date,
    end_date: date,
    vendors: list[str],
    sale_origins: list[str],
    order_types: list[str],
    order_statuses: list[str] | None,
) -> pd.DataFrame:
    df = pedidos.copy()
    df = df[(df["ORDER_DATE"] >= pd.Timestamp(start_date)) & (df["ORDER_DATE"] <= pd.Timestamp(end_date))]
    if vendors and "SELLER_NAME" in df.columns:
        df = df[df["SELLER_NAME"].isin(vendors)]
    elif vendors == [] and "SELLER_NAME" in df.columns:
        return df.iloc[0:0]
    if sale_origins and "ORIGEN_VENTA" in df.columns:
        df = df[df["ORIGEN_VENTA"].isin(sale_origins)]
    elif sale_origins == [] and "ORIGEN_VENTA" in df.columns:
        return df.iloc[0:0]
    if order_types and "TIPO_ORDEN" in df.columns:
        df = df[df["TIPO_ORDEN"].isin(order_types)]
    elif order_types == [] and "TIPO_ORDEN" in df.columns:
        return df.iloc[0:0]
    if order_statuses is None:
        return df
    if order_statuses and "STATUS" in df.columns:
        df = df[df["STATUS"].isin(order_statuses)]
    elif order_statuses == [] and "STATUS" in df.columns:
        return df.iloc[0:0]
    return df
