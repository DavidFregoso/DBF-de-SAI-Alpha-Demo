from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import calendar

import pandas as pd
import streamlit as st

from sai_alpha.etl import DataBundle
from sai_alpha.perf import perf_logger
from sai_alpha.ui import normalize_currency, record_schema_message, validate_sales_schema


@dataclass
class FilterState:
    start_date: date
    end_date: date
    granularity: str
    currency_mode: str
    period_type: str
    period_label: str
    period_selection_label: str | None
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
    clients: pd.DataFrame
    products: pd.DataFrame
    pedidos: pd.DataFrame | None
    currency_label: str
    revenue_column: str
    unit_price_column: str
    fx_average: float | None
    filter_key: str


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


@st.cache_data(show_spinner=False)
def compute_available_periods(df_sales: pd.DataFrame) -> dict[str, object]:
    if df_sales.empty or "SALE_DATE" not in df_sales.columns:
        today = date.today()
        iso = today.isocalendar()
        return {
            "min_date": today,
            "max_date": today,
            "latest_week_year": iso.year,
            "latest_week": iso.week,
            "latest_month_year": today.year,
            "latest_month": today.month,
            "latest_year": today.year,
            "years": [today.year],
            "weeks_by_year": {today.year: [iso.week]},
            "months_by_year": {today.year: [today.month]},
        }

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
    return {
        "min_date": min_date,
        "max_date": max_date,
        "latest_week_year": int(latest_iso.year),
        "latest_week": int(latest_iso.week),
        "latest_month_year": int(max_date.year),
        "latest_month": int(max_date.month),
        "latest_year": int(max_date.year),
        "years": sorted(sales_dates.dt.year.unique().tolist()),
        "weeks_by_year": weeks_by_year,
        "months_by_year": months_by_year,
    }


def _init_multiselect_state(key: str, options: list[str]) -> None:
    if key not in st.session_state:
        st.session_state[key] = options
        return
    current = st.session_state[key]
    if not current:
        return
    st.session_state[key] = [value for value in current if value in options]


def multiselect_with_actions(container, label: str, options: list[str] | None, key: str) -> list[str]:
    # container puede ser None si no se creó el expander.
    safe_container = container if container is not None else st.sidebar
    safe_options = options or []
    _init_multiselect_state(key, safe_options)
    try:
        col1, col2 = safe_container.columns(2)
    except AttributeError:
        col1, col2 = st.columns(2)
    if col1.button("Seleccionar todo", key=f"{key}_all"):
        st.session_state[key] = safe_options
    if col2.button("Limpiar", key=f"{key}_clear"):
        st.session_state[key] = []
    return safe_container.multiselect(label, safe_options, key=key)


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


def _format_week_label(week: int, year: int) -> str:
    return f"Semana {int(week):02d} - {int(year)}"


def _format_month_label(month: int, year: int) -> str:
    month_names = [
        "",
        "Enero",
        "Febrero",
        "Marzo",
        "Abril",
        "Mayo",
        "Junio",
        "Julio",
        "Agosto",
        "Septiembre",
        "Octubre",
        "Noviembre",
        "Diciembre",
    ]
    return f"{month_names[int(month)]} {int(year)}"


def _format_year_label(year: int) -> str:
    return f"{year}"


def _latest_available_period(periods: dict[str, object]) -> tuple[date, date, str]:
    if periods.get("months_by_year"):
        year = int(periods["latest_month_year"])
        month = int(periods["latest_month"])
        start_date, end_date = _month_range_from_selection(year, month)
        return start_date, end_date, _format_month_label(month, year)
    if periods.get("weeks_by_year"):
        year = int(periods["latest_week_year"])
        week = int(periods["latest_week"])
        start_date, end_date = _week_range_from_selection(year, week)
        return start_date, end_date, _format_week_label(week, year)
    end_date = periods["max_date"]
    start_date = max(periods["min_date"], end_date - timedelta(days=29))
    return start_date, end_date, f"{start_date.isoformat()} a {end_date.isoformat()}"


def _recommended_granularity(days_range: int) -> str:
    if days_range <= 31:
        return "Diario"
    if days_range <= 120:
        return "Semanal"
    return "Mensual"


def _normalize_filter_list(values: list[str] | None) -> tuple[str, ...]:
    if not values:
        return tuple()
    return tuple(sorted({str(value) for value in values}))


def build_filter_key(
    start_date: date,
    end_date: date,
    currency_mode: str,
    granularity: str,
    brands: list[str] | None,
    categories: list[str] | None,
    vendors: list[str] | None,
    sale_origins: list[str] | None,
    client_origins: list[str] | None,
    recommendation_sources: list[str] | None,
    invoice_types: list[str] | None,
    order_types: list[str] | None,
    order_statuses: list[str] | None,
) -> str:
    def _serialize(values: list[str] | None) -> str:
        if not values:
            return "ALL"
        return ",".join(sorted({str(value) for value in values}))

    return (
        f"{start_date.isoformat()}|{end_date.isoformat()}|{currency_mode}|{granularity}"
        f"|brands:{_serialize(brands)}"
        f"|categories:{_serialize(categories)}"
        f"|vendors:{_serialize(vendors)}"
        f"|sale_origins:{_serialize(sale_origins)}"
        f"|client_origins:{_serialize(client_origins)}"
        f"|recommendation_sources:{_serialize(recommendation_sources)}"
        f"|invoice_types:{_serialize(invoice_types)}"
        f"|order_types:{_serialize(order_types)}"
        f"|order_statuses:{_serialize(order_statuses)}"
    )


def build_global_filters(df_sales: pd.DataFrame) -> dict[str, object]:
    periods = compute_available_periods(df_sales)
    st.session_state.setdefault("period_type", "Último periodo disponible (recomendado)")
    st.session_state.setdefault("granularity", "Auto")
    st.session_state.setdefault("currency_view", "MXN")
    st.session_state.setdefault("selected_year", periods["latest_year"])
    st.session_state.setdefault("selected_month", periods["latest_month"])
    st.session_state.setdefault("selected_month_year", periods["latest_month_year"])
    st.session_state.setdefault("selected_week", periods["latest_week"])
    st.session_state.setdefault("selected_week_year", periods["latest_week_year"])
    st.session_state.setdefault("range_start", periods["min_date"])
    st.session_state.setdefault("range_end", periods["max_date"])
    st.session_state.setdefault("last_valid_range", (periods["min_date"], periods["max_date"]))

    st.sidebar.markdown("**Periodo**")
    period_type = st.sidebar.selectbox(
        "Tipo de periodo",
        [
            "Último periodo disponible (recomendado)",
            "Mes",
            "Semana",
            "Año",
            "Rango de fechas",
        ],
        key="period_type",
    )

    period_selection_label = None
    if period_type == "Último periodo disponible (recomendado)":
        start_date, end_date, period_selection_label = _latest_available_period(periods)
    elif period_type == "Mes":
        month_options = [
            (int(year), int(month))
            for year in sorted(periods["months_by_year"])
            for month in periods["months_by_year"][year]
        ]
        if not month_options:
            month_options = [(int(periods["latest_month_year"]), int(periods["latest_month"]))]
        default_option = (int(st.session_state["selected_month_year"]), int(st.session_state["selected_month"]))
        if default_option not in month_options:
            default_option = month_options[-1]
        st.session_state.setdefault("selected_month_option", default_option)
        selection = st.sidebar.selectbox(
            "Mes",
            month_options,
            key="selected_month_option",
            format_func=lambda value: _format_month_label(value[1], value[0]),
        )
        st.session_state["selected_month_year"] = selection[0]
        st.session_state["selected_month"] = selection[1]
        start_date, end_date = _month_range_from_selection(selection[0], selection[1])
        period_selection_label = _format_month_label(selection[1], selection[0])
    elif period_type == "Semana":
        week_options = [
            (int(year), int(week))
            for year in sorted(periods["weeks_by_year"])
            for week in periods["weeks_by_year"][year]
        ]
        if not week_options:
            week_options = [(int(periods["latest_week_year"]), int(periods["latest_week"]))]
        default_option = (int(st.session_state["selected_week_year"]), int(st.session_state["selected_week"]))
        if default_option not in week_options:
            default_option = week_options[-1]
        st.session_state.setdefault("selected_week_option", default_option)
        selection = st.sidebar.selectbox(
            "Semana",
            week_options,
            key="selected_week_option",
            format_func=lambda value: _format_week_label(value[1], value[0]),
        )
        st.session_state["selected_week_year"] = selection[0]
        st.session_state["selected_week"] = selection[1]
        start_date, end_date = _week_range_from_selection(selection[0], selection[1])
        period_selection_label = _format_week_label(selection[1], selection[0])
    elif period_type == "Año":
        years = periods["years"] or [periods["latest_year"]]
        selection = st.sidebar.selectbox("Año", years, key="selected_year", format_func=_format_year_label)
        start_date, end_date = _year_range_from_selection(int(selection))
        period_selection_label = _format_year_label(int(selection))
    else:
        start_input = st.sidebar.date_input(
            "Inicio",
            key="range_start",
            min_value=periods["min_date"],
            max_value=periods["max_date"],
        )
        end_input = st.sidebar.date_input(
            "Fin",
            key="range_end",
            min_value=periods["min_date"],
            max_value=periods["max_date"],
        )
        if st.sidebar.button("Aplicar rango", key="apply_date_range"):
            if end_input < start_input:
                st.sidebar.error("La fecha final no puede ser menor a la inicial.")
            else:
                st.session_state["last_valid_range"] = (start_input, end_input)
        last_valid_range = st.session_state.get("last_valid_range", (start_input, end_input))
        start_date, end_date = last_valid_range

    currency_view = st.sidebar.selectbox("Moneda", ["MXN", "USD"], key="currency_view")
    granularity_choice = st.sidebar.selectbox(
        "Granularidad",
        ["Auto", "Diario", "Semanal", "Mensual"],
        key="granularity",
    )

    if st.sidebar.button("Actualizar ahora", key="refresh_now"):
        refreshed_at = datetime.now()
        st.session_state["last_refresh_ts"] = refreshed_at
        st.toast(f"Datos actualizados: {refreshed_at:%d/%m/%Y %H:%M}")

    last_refresh = st.session_state.get("last_refresh_ts")
    if last_refresh:
        st.sidebar.caption(f"Última actualización: {last_refresh:%d/%m/%Y %H:%M}")
    else:
        st.sidebar.caption("Última actualización: pendiente")

    days_range = max(1, (end_date - start_date).days + 1)
    recommended = _recommended_granularity(days_range)
    granularity = recommended if granularity_choice == "Auto" else granularity_choice

    period_label = period_selection_label or period_type
    st.sidebar.caption(f"Del: {start_date.isoformat()}  Al: {end_date.isoformat()}")
    if period_selection_label:
        st.sidebar.caption(f"Periodo seleccionado: {period_selection_label}")

    return {
        "start_date": start_date,
        "end_date": end_date,
        "granularity": granularity,
        "currency_view": currency_view,
        "period_type": period_type,
        "period_label": period_label,
        "period_selection_label": period_selection_label,
    }


def build_advanced_filters(
    df_sales: pd.DataFrame,
    df_orders: pd.DataFrame | None,
    context: AdvancedFilterContext,
    container=None,
) -> dict[str, list[str] | None]:
    if df_sales is None:
        st.sidebar.info("Ventas no cargadas; filtros avanzados deshabilitados")
        return {}
    if df_orders is None:
        st.sidebar.info("Pedidos no cargados; filtros avanzados deshabilitados")
        return {}

    def _default_options(frame: pd.DataFrame | None, column: str) -> list[str]:
        if frame is None or column not in frame.columns:
            return []
        return sorted(frame[column].dropna().unique().tolist())

    expander = container
    filters: dict[str, list[str] | None] = {}

    if context.brands:
        options = _default_options(df_sales, "BRAND")
        filters["brands"] = multiselect_with_actions(expander, "Marca", options, "filter_brands")
    else:
        filters["brands"] = _default_options(df_sales, "BRAND")

    if context.categories:
        options = _default_options(df_sales, "CATEGORY")
        filters["categories"] = multiselect_with_actions(expander, "Categoría", options, "filter_categories")
    else:
        filters["categories"] = _default_options(df_sales, "CATEGORY")

    if context.vendors:
        options = _default_options(df_sales, "SELLER_NAME")
        filters["vendors"] = multiselect_with_actions(expander, "Vendedor", options, "filter_vendors")
    else:
        filters["vendors"] = _default_options(df_sales, "SELLER_NAME")

    if context.sale_origins:
        options = _default_options(df_sales, "ORIGEN_VENTA")
        filters["sale_origins"] = multiselect_with_actions(
            expander, "Origen de venta", options, "filter_sale_origins"
        )
    else:
        filters["sale_origins"] = _default_options(df_sales, "ORIGEN_VENTA")

    if context.client_origins:
        options = _default_options(df_sales, "CLIENT_ORIGIN")
        filters["client_origins"] = multiselect_with_actions(
            expander, "Origen de cliente", options, "filter_client_origins"
        )
    else:
        filters["client_origins"] = _default_options(df_sales, "CLIENT_ORIGIN")

    if context.recommendation_sources:
        options = _default_options(df_sales, "RECOMM_SOURCE")
        filters["recommendation_sources"] = multiselect_with_actions(
            expander,
            "Recomendación / encuesta",
            options,
            "filter_recommendations",
        )
    else:
        filters["recommendation_sources"] = _default_options(df_sales, "RECOMM_SOURCE")

    if context.invoice_types:
        options = _default_options(df_sales, "TIPO_FACTURA")
        filters["invoice_types"] = multiselect_with_actions(
            expander, "Tipo de factura", options, "filter_invoice_types"
        )
    else:
        filters["invoice_types"] = _default_options(df_sales, "TIPO_FACTURA")

    if context.order_types:
        options = _default_options(df_sales, "TIPO_ORDEN")
        filters["order_types"] = multiselect_with_actions(
            expander, "Tipo de orden", options, "filter_order_types"
        )
    else:
        filters["order_types"] = _default_options(df_sales, "TIPO_ORDEN")

    if context.order_statuses and df_orders is not None and not df_orders.empty:
        options = _default_options(df_orders, "STATUS")
        filters["order_statuses"] = multiselect_with_actions(
            expander, "Estatus de pedido", options, "filter_order_statuses"
        )
    else:
        filters["order_statuses"] = None

    return filters


def apply_sales_filters(
    ventas: pd.DataFrame,
    start_date: date,
    end_date: date,
    brands: tuple[str, ...],
    categories: tuple[str, ...],
    vendors: tuple[str, ...],
    sale_origins: tuple[str, ...],
    client_origins: tuple[str, ...],
    recommendation_sources: tuple[str, ...],
    invoice_types: tuple[str, ...],
    order_types: tuple[str, ...],
) -> pd.DataFrame:
    df = ventas
    mask = pd.Series(True, index=df.index)
    if "SALE_DATE" in df.columns:
        mask &= (df["SALE_DATE"] >= pd.Timestamp(start_date)) & (df["SALE_DATE"] <= pd.Timestamp(end_date))
    if "BRAND" in df.columns and brands:
        mask &= df["BRAND"].isin(brands)
    if "CATEGORY" in df.columns and categories:
        mask &= df["CATEGORY"].isin(categories)
    if "SELLER_NAME" in df.columns and vendors:
        mask &= df["SELLER_NAME"].isin(vendors)
    if "ORIGEN_VENTA" in df.columns and sale_origins:
        mask &= df["ORIGEN_VENTA"].isin(sale_origins)
    if "CLIENT_ORIGIN" in df.columns and client_origins:
        mask &= df["CLIENT_ORIGIN"].isin(client_origins)
    if "RECOMM_SOURCE" in df.columns and recommendation_sources:
        mask &= df["RECOMM_SOURCE"].isin(recommendation_sources)
    if "TIPO_FACTURA" in df.columns and invoice_types:
        mask &= df["TIPO_FACTURA"].isin(invoice_types)
    if "TIPO_ORDEN" in df.columns and order_types:
        mask &= df["TIPO_ORDEN"].isin(order_types)
    return df.loc[mask]


def apply_order_filters(
    pedidos: pd.DataFrame,
    start_date: date,
    end_date: date,
    vendors: tuple[str, ...],
    sale_origins: tuple[str, ...],
    order_types: tuple[str, ...],
    order_statuses: tuple[str, ...] | None,
) -> pd.DataFrame:
    df = pedidos
    mask = pd.Series(True, index=df.index)
    if "ORDER_DATE" in df.columns:
        mask &= (df["ORDER_DATE"] >= pd.Timestamp(start_date)) & (df["ORDER_DATE"] <= pd.Timestamp(end_date))
    if vendors and "SELLER_NAME" in df.columns:
        mask &= df["SELLER_NAME"].isin(vendors)
    if sale_origins and "ORIGEN_VENTA" in df.columns:
        mask &= df["ORIGEN_VENTA"].isin(sale_origins)
    if order_types and "TIPO_ORDEN" in df.columns:
        mask &= df["TIPO_ORDEN"].isin(order_types)
    if order_statuses and "STATUS" in df.columns:
        mask &= df["STATUS"].isin(order_statuses)
    return df.loc[mask]


@st.cache_data(show_spinner=False)
def cached_apply_sales_filters(
    ventas: pd.DataFrame,
    start_date: date,
    end_date: date,
    brands: tuple[str, ...],
    categories: tuple[str, ...],
    vendors: tuple[str, ...],
    sale_origins: tuple[str, ...],
    client_origins: tuple[str, ...],
    recommendation_sources: tuple[str, ...],
    invoice_types: tuple[str, ...],
    order_types: tuple[str, ...],
    filter_key: str,
) -> pd.DataFrame:
    return apply_sales_filters(
        ventas,
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


@st.cache_data(show_spinner=False)
def cached_apply_order_filters(
    pedidos: pd.DataFrame,
    start_date: date,
    end_date: date,
    vendors: tuple[str, ...],
    sale_origins: tuple[str, ...],
    order_types: tuple[str, ...],
    order_statuses: tuple[str, ...] | None,
    filter_key: str,
) -> pd.DataFrame:
    return apply_order_filters(
        pedidos,
        start_date,
        end_date,
        vendors,
        sale_origins,
        order_types,
        order_statuses,
    )


@st.cache_data(show_spinner=False)
def filter_data(
    ventas: pd.DataFrame,
    pedidos: pd.DataFrame | None,
    clientes: pd.DataFrame,
    productos: pd.DataFrame,
    start_date: date,
    end_date: date,
    brands: tuple[str, ...],
    categories: tuple[str, ...],
    vendors: tuple[str, ...],
    sale_origins: tuple[str, ...],
    client_origins: tuple[str, ...],
    recommendation_sources: tuple[str, ...],
    invoice_types: tuple[str, ...],
    order_types: tuple[str, ...],
    order_statuses: tuple[str, ...] | None,
    filter_key: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame | None]:
    ventas_filtrado = apply_sales_filters(
        ventas,
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
    pedidos_filtrado = None
    if pedidos is not None and not pedidos.empty:
        pedidos_filtrado = apply_order_filters(
            pedidos,
            start_date,
            end_date,
            vendors,
            sale_origins,
            order_types,
            order_statuses,
        )
    clientes_filtrado = clientes.copy()
    if not ventas_filtrado.empty and "CLIENT_ID" in ventas_filtrado.columns and "CLIENT_ID" in clientes_filtrado.columns:
        clientes_filtrado = clientes_filtrado[clientes_filtrado["CLIENT_ID"].isin(ventas_filtrado["CLIENT_ID"].unique())]

    productos_filtrado = productos.copy()
    if not ventas_filtrado.empty and "PRODUCT_ID" in ventas_filtrado.columns and "PRODUCT_ID" in productos_filtrado.columns:
        productos_filtrado = productos_filtrado[productos_filtrado["PRODUCT_ID"].isin(ventas_filtrado["PRODUCT_ID"].unique())]

    return ventas_filtrado, clientes_filtrado, productos_filtrado, pedidos_filtrado


def apply_global_filters(
    bundle: DataBundle,
    filters: FilterState,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame | None]:
    ventas_filtrado = filters.sales.copy()

    clientes_filtrado = bundle.clientes.copy()
    if not ventas_filtrado.empty and "CLIENT_ID" in ventas_filtrado.columns and "CLIENT_ID" in clientes_filtrado.columns:
        clientes_filtrado = clientes_filtrado[clientes_filtrado["CLIENT_ID"].isin(ventas_filtrado["CLIENT_ID"].unique())]

    productos_filtrado = bundle.productos.copy()
    if not ventas_filtrado.empty and "PRODUCT_ID" in ventas_filtrado.columns and "PRODUCT_ID" in productos_filtrado.columns:
        productos_filtrado = productos_filtrado[productos_filtrado["PRODUCT_ID"].isin(ventas_filtrado["PRODUCT_ID"].unique())]

    pedidos_filtrado = None
    if bundle.pedidos is not None and not bundle.pedidos.empty:
        pedidos_filtrado = apply_order_filters(
            bundle.pedidos,
            filters.start_date,
            filters.end_date,
            filters.vendors,
            filters.sale_origins,
            filters.order_types,
            filters.order_statuses,
        )
    return ventas_filtrado, clientes_filtrado, productos_filtrado, pedidos_filtrado


def build_filter_state(
    ventas: pd.DataFrame,
    pedidos: pd.DataFrame | None,
    bundle: DataBundle,
    global_filters: dict[str, object],
    advanced_filters: dict[str, list[str] | None],
) -> FilterState:
    missing_columns = validate_sales_schema(ventas)
    if missing_columns:
        record_schema_message(
            "Columnas faltantes en ventas (se usarán fallbacks): " + ", ".join(missing_columns)
        )

    ventas_normalized, revenue_column, unit_price_column, currency_label = normalize_currency(
        ventas, str(global_filters["currency_view"])
    )

    filter_key = build_filter_key(
        global_filters["start_date"],
        global_filters["end_date"],
        str(global_filters["currency_view"]),
        str(global_filters["granularity"]),
        advanced_filters.get("brands"),
        advanced_filters.get("categories"),
        advanced_filters.get("vendors"),
        advanced_filters.get("sale_origins"),
        advanced_filters.get("client_origins"),
        advanced_filters.get("recommendation_sources"),
        advanced_filters.get("invoice_types"),
        advanced_filters.get("order_types"),
        advanced_filters.get("order_statuses"),
    )

    brands = _normalize_filter_list(advanced_filters.get("brands"))
    categories = _normalize_filter_list(advanced_filters.get("categories"))
    vendors = _normalize_filter_list(advanced_filters.get("vendors"))
    sale_origins = _normalize_filter_list(advanced_filters.get("sale_origins"))
    client_origins = _normalize_filter_list(advanced_filters.get("client_origins"))
    recommendation_sources = _normalize_filter_list(advanced_filters.get("recommendation_sources"))
    invoice_types = _normalize_filter_list(advanced_filters.get("invoice_types"))
    order_types = _normalize_filter_list(advanced_filters.get("order_types"))
    order_statuses = _normalize_filter_list(advanced_filters.get("order_statuses"))

    with perf_logger("filter_data"):
        sales_filtered, clients_filtered, products_filtered, pedidos_filtered = filter_data(
            ventas_normalized,
            pedidos,
            bundle.clientes.copy() if bundle.clientes is not None else pd.DataFrame(),
            bundle.productos.copy() if bundle.productos is not None else pd.DataFrame(),
            global_filters["start_date"],
            global_filters["end_date"],
            brands,
            categories,
            vendors,
            sale_origins,
            client_origins,
            recommendation_sources,
            invoice_types,
            order_types,
            order_statuses if order_statuses else None,
            filter_key,
        )

    fx_average = None
    if "USD_MXN_RATE" in ventas_normalized.columns:
        fx_filtered = ventas_normalized[
            (ventas_normalized["SALE_DATE"] >= pd.Timestamp(global_filters["start_date"]))
            & (ventas_normalized["SALE_DATE"] <= pd.Timestamp(global_filters["end_date"]))
        ]
        fx_series = fx_filtered["USD_MXN_RATE"].dropna()
        fx_average = float(fx_series.mean()) if not fx_series.empty else None

    filter_state = FilterState(
        start_date=global_filters["start_date"],
        end_date=global_filters["end_date"],
        granularity=str(global_filters["granularity"]),
        currency_mode=str(global_filters["currency_view"]),
        period_type=str(global_filters["period_type"]),
        period_label=str(global_filters["period_label"]),
        period_selection_label=global_filters.get("period_selection_label"),
        brands=list(brands),
        categories=list(categories),
        vendors=list(vendors),
        sale_origins=list(sale_origins),
        client_origins=list(client_origins),
        recommendation_sources=list(recommendation_sources),
        invoice_types=list(invoice_types),
        order_types=list(order_types),
        order_statuses=list(order_statuses) if order_statuses else None,
        sales=sales_filtered,
        clients=clients_filtered,
        products=products_filtered,
        pedidos=pedidos_filtered,
        currency_label=currency_label,
        revenue_column=revenue_column,
        unit_price_column=unit_price_column,
        fx_average=fx_average,
        filter_key=filter_key,
    )

    return filter_state
