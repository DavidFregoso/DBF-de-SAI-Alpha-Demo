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
    period_mode: str
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


@dataclass
class AdvancedFilterContext:
    brands: bool = False
    categories: bool = False
    vendors: bool = False
    sale_origins: bool = False
    client_origins: bool = False
    recommendation_sources: bool = False
    invoice_types: bool = False
    order_types: bool = False
    order_statuses: bool = False


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


def _ensure_latest_periods(df_sales: pd.DataFrame) -> LatestPeriods:
    latest: LatestPeriods | None = st.session_state.get("latest_periods")
    if latest is None:
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
        latest = LatestPeriods(
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
        st.session_state["latest_periods"] = latest
    return latest


def build_global_filters(df_sales: pd.DataFrame) -> dict[str, object]:
    latest = _ensure_latest_periods(df_sales)
    st.session_state.setdefault("period_mode", "Último periodo")
    st.session_state.setdefault("granularity", "Semanal")
    st.session_state.setdefault("currency_view", "MXN")
    st.session_state.setdefault("period_year", latest.latest_year)
    st.session_state.setdefault("period_month", latest.latest_month)
    st.session_state.setdefault("period_month_year", latest.latest_month_year)
    st.session_state.setdefault("period_week", latest.latest_week)
    st.session_state.setdefault("period_week_year", latest.latest_week_year)
    st.session_state.setdefault("date_start", latest.min_date)
    st.session_state.setdefault("date_end", latest.max_date)

    period_mode = st.sidebar.selectbox(
        "Modo de periodo",
        ["Último periodo", "Semana (ISO)", "Mes", "Rango de fechas", "Año"],
        key="period_mode",
    )

    granularity = st.sidebar.selectbox(
        "Granularidad",
        ["Diario", "Semanal", "Mensual"],
        key="granularity",
    )

    currency_view = st.sidebar.selectbox(
        "Moneda",
        ["MXN", "USD"],
        key="currency_view",
    )

    if period_mode == "Último periodo":
        max_date = latest.max_date
        if granularity == "Diario":
            start_date = max_date
            end_date = max_date
        elif granularity == "Mensual":
            start_date, end_date = _month_range_from_selection(max_date.year, max_date.month)
        else:
            iso = max_date.isocalendar()
            start_date, end_date = _week_range_from_selection(int(iso.year), int(iso.week))
    elif period_mode == "Semana (ISO)":
        year = st.sidebar.selectbox("Año", latest.years, key="period_week_year")
        weeks = latest.weeks_by_year.get(int(year), [latest.latest_week])
        if st.session_state.get("period_week") not in weeks:
            st.session_state["period_week"] = weeks[-1]
        week = st.sidebar.selectbox("Semana", weeks, key="period_week")
        start_date, end_date = _week_range_from_selection(int(year), int(week))
    elif period_mode == "Mes":
        year = st.sidebar.selectbox("Año", latest.years, key="period_month_year")
        months = latest.months_by_year.get(int(year), [latest.latest_month])
        if st.session_state.get("period_month") not in months:
            st.session_state["period_month"] = months[-1]
        month = st.sidebar.selectbox(
            "Mes",
            months,
            format_func=lambda value: calendar.month_name[int(value)],
            key="period_month",
        )
        start_date, end_date = _month_range_from_selection(int(year), int(month))
    elif period_mode == "Rango de fechas":
        date_start, date_end = st.sidebar.date_input(
            "Rango",
            value=(st.session_state["date_start"], st.session_state["date_end"]),
            min_value=latest.min_date,
            max_value=latest.max_date,
        )
        st.session_state["date_start"] = date_start
        st.session_state["date_end"] = date_end
        start_date, end_date = date_start, date_end
    else:
        year = st.sidebar.selectbox("Año", latest.years, key="period_year")
        start_date, end_date = _year_range_from_selection(int(year))

    st.sidebar.caption(f"Del: {start_date.isoformat()}  Al: {end_date.isoformat()}")

    return {
        "start_date": start_date,
        "end_date": end_date,
        "granularity": granularity,
        "currency_view": currency_view,
        "period_mode": period_mode,
    }


def build_advanced_filters(
    df_sales: pd.DataFrame,
    df_orders: pd.DataFrame | None,
    context: AdvancedFilterContext,
) -> dict[str, list[str] | None]:
    def _default_options(frame: pd.DataFrame, column: str) -> list[str]:
        if column not in frame.columns:
            return []
        return sorted(frame[column].dropna().unique().tolist())

    if not any(
        [
            context.brands,
            context.categories,
            context.vendors,
            context.sale_origins,
            context.client_origins,
            context.recommendation_sources,
            context.invoice_types,
            context.order_types,
            context.order_statuses,
        ]
    ):
        return {
            "brands": _default_options(df_sales, "BRAND"),
            "categories": _default_options(df_sales, "CATEGORY"),
            "vendors": _default_options(df_sales, "SELLER_NAME"),
            "sale_origins": _default_options(df_sales, "ORIGEN_VENTA"),
            "client_origins": _default_options(df_sales, "CLIENT_ORIGIN"),
            "recommendation_sources": _default_options(df_sales, "RECOMM_SOURCE"),
            "invoice_types": _default_options(df_sales, "TIPO_FACTURA"),
            "order_types": _default_options(df_sales, "TIPO_ORDEN"),
            "order_statuses": None,
        }

    with st.sidebar.expander("Filtros avanzados", expanded=False):
        filters: dict[str, list[str] | None] = {}

        if context.brands and "BRAND" in df_sales.columns:
            options = sorted(df_sales["BRAND"].dropna().unique().tolist())
            filters["brands"] = multiselect_with_actions("Marca", options, "filter_brands")
        else:
            filters["brands"] = _default_options(df_sales, "BRAND")

        if context.categories and "CATEGORY" in df_sales.columns:
            options = sorted(df_sales["CATEGORY"].dropna().unique().tolist())
            filters["categories"] = multiselect_with_actions("Categoría", options, "filter_categories")
        else:
            filters["categories"] = _default_options(df_sales, "CATEGORY")

        if context.vendors and "SELLER_NAME" in df_sales.columns:
            options = sorted(df_sales["SELLER_NAME"].dropna().unique().tolist())
            filters["vendors"] = multiselect_with_actions("Vendedor", options, "filter_vendors")
        else:
            filters["vendors"] = _default_options(df_sales, "SELLER_NAME")

        if context.sale_origins and "ORIGEN_VENTA" in df_sales.columns:
            options = sorted(df_sales["ORIGEN_VENTA"].dropna().unique().tolist())
            filters["sale_origins"] = multiselect_with_actions(
                "Origen de venta", options, "filter_sale_origins"
            )
        else:
            filters["sale_origins"] = _default_options(df_sales, "ORIGEN_VENTA")

        if context.client_origins and "CLIENT_ORIGIN" in df_sales.columns:
            options = sorted(df_sales["CLIENT_ORIGIN"].dropna().unique().tolist())
            filters["client_origins"] = multiselect_with_actions(
                "Origen de cliente", options, "filter_client_origins"
            )
        else:
            filters["client_origins"] = _default_options(df_sales, "CLIENT_ORIGIN")

        if context.recommendation_sources and "RECOMM_SOURCE" in df_sales.columns:
            options = sorted(df_sales["RECOMM_SOURCE"].dropna().unique().tolist())
            filters["recommendation_sources"] = multiselect_with_actions(
                "Recomendación / encuesta",
                options,
                "filter_recommendations",
            )
        else:
            filters["recommendation_sources"] = _default_options(df_sales, "RECOMM_SOURCE")

        if context.invoice_types and "TIPO_FACTURA" in df_sales.columns:
            options = sorted(df_sales["TIPO_FACTURA"].dropna().unique().tolist())
            filters["invoice_types"] = multiselect_with_actions(
                "Tipo de factura", options, "filter_invoice_types"
            )
        else:
            filters["invoice_types"] = _default_options(df_sales, "TIPO_FACTURA")

        if context.order_types and "TIPO_ORDEN" in df_sales.columns:
            options = sorted(df_sales["TIPO_ORDEN"].dropna().unique().tolist())
            filters["order_types"] = multiselect_with_actions(
                "Tipo de orden", options, "filter_order_types"
            )
        else:
            filters["order_types"] = _default_options(df_sales, "TIPO_ORDEN")

        if context.order_statuses and df_orders is not None and not df_orders.empty:
            if "STATUS" in df_orders.columns:
                options = sorted(df_orders["STATUS"].dropna().unique().tolist())
                filters["order_statuses"] = multiselect_with_actions(
                    "Estatus de pedido", options, "filter_order_statuses"
                )
            else:
                filters["order_statuses"] = None
        else:
            filters["order_statuses"] = None

    return filters


def build_filter_state(
    ventas: pd.DataFrame,
    pedidos: pd.DataFrame | None,
    global_filters: dict[str, object],
    advanced_filters: dict[str, list[str] | None],
) -> FilterState:
    missing_columns = validate_sales_schema(ventas)
    if missing_columns:
        st.sidebar.error(
            "Faltan columnas requeridas en la tabla de ventas: " + ", ".join(missing_columns)
        )
        st.stop()

    ventas_normalized, revenue_column, unit_price_column, currency_label = normalize_currency(
        ventas, str(global_filters["currency_view"])
    )

    sales_filtered = apply_sales_filters(
        ventas_normalized,
        global_filters["start_date"],
        global_filters["end_date"],
        advanced_filters.get("brands", []),
        advanced_filters.get("categories", []),
        advanced_filters.get("vendors", []),
        advanced_filters.get("sale_origins", []),
        advanced_filters.get("client_origins", []),
        advanced_filters.get("recommendation_sources", []),
        advanced_filters.get("invoice_types", []),
        advanced_filters.get("order_types", []),
    )

    pedidos_filtered = None
    if pedidos is not None and not pedidos.empty:
        pedidos_filtered = apply_order_filters(
            pedidos,
            global_filters["start_date"],
            global_filters["end_date"],
            advanced_filters.get("vendors", []),
            advanced_filters.get("sale_origins", []),
            advanced_filters.get("order_types", []),
            advanced_filters.get("order_statuses"),
        )

    st.sidebar.caption(f"Registros filtrados: {len(sales_filtered):,}")

    fx_average = None
    if "USD_MXN_RATE" in ventas_normalized.columns:
        fx_filtered = ventas_normalized[
            (ventas_normalized["SALE_DATE"] >= pd.Timestamp(global_filters["start_date"]))
            & (ventas_normalized["SALE_DATE"] <= pd.Timestamp(global_filters["end_date"]))
        ]
        fx_series = fx_filtered["USD_MXN_RATE"].dropna()
        fx_average = float(fx_series.mean()) if not fx_series.empty else None

    return FilterState(
        start_date=global_filters["start_date"],
        end_date=global_filters["end_date"],
        granularity=str(global_filters["granularity"]),
        currency_mode=str(global_filters["currency_view"]),
        period_mode=str(global_filters["period_mode"]),
        brands=advanced_filters.get("brands", []),
        categories=advanced_filters.get("categories", []),
        vendors=advanced_filters.get("vendors", []),
        sale_origins=advanced_filters.get("sale_origins", []),
        client_origins=advanced_filters.get("client_origins", []),
        recommendation_sources=advanced_filters.get("recommendation_sources", []),
        invoice_types=advanced_filters.get("invoice_types", []),
        order_types=advanced_filters.get("order_types", []),
        order_statuses=advanced_filters.get("order_statuses"),
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
    if "BRAND" in df.columns:
        if brands:
            df = df[df["BRAND"].isin(brands)]
        else:
            return df.iloc[0:0]
    if "CATEGORY" in df.columns:
        if categories:
            df = df[df["CATEGORY"].isin(categories)]
        else:
            return df.iloc[0:0]
    if "SELLER_NAME" in df.columns:
        if vendors:
            df = df[df["SELLER_NAME"].isin(vendors)]
        else:
            return df.iloc[0:0]
    if "ORIGEN_VENTA" in df.columns:
        if sale_origins:
            df = df[df["ORIGEN_VENTA"].isin(sale_origins)]
        else:
            return df.iloc[0:0]
    if "CLIENT_ORIGIN" in df.columns:
        if client_origins:
            df = df[df["CLIENT_ORIGIN"].isin(client_origins)]
        else:
            return df.iloc[0:0]
    if "RECOMM_SOURCE" in df.columns:
        if recommendation_sources:
            df = df[df["RECOMM_SOURCE"].isin(recommendation_sources)]
        else:
            return df.iloc[0:0]
    if "TIPO_FACTURA" in df.columns:
        if invoice_types:
            df = df[df["TIPO_FACTURA"].isin(invoice_types)]
        else:
            return df.iloc[0:0]
    if "TIPO_ORDEN" in df.columns:
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
