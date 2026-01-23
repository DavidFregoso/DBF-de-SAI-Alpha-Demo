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
    period_mode: str
    range_mode: str
    period_label: str
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
    start, end = _week_range_from_selection(year, week)
    return f"Semana {int(week):02d} ({start.isoformat()} a {end.isoformat()})"


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
    start, end = _month_range_from_selection(year, month)
    return f"{month_names[int(month)]} {int(year)} ({start.isoformat()} a {end.isoformat()})"


def _format_year_label(year: int) -> str:
    start, end = _year_range_from_selection(year)
    return f"{year} ({start.isoformat()} a {end.isoformat()})"


def normalize_period(
    filters: dict[str, object],
    periods: dict[str, object],
) -> tuple[date, date, str, str]:
    period_mode = str(filters["period_mode"])
    range_mode = str(filters["range_mode"])
    granularity_choice = str(filters["granularity"])

    if period_mode == "Último periodo disponible":
        if range_mode == "Semana":
            start_date, end_date = _week_range_from_selection(
                int(periods["latest_week_year"]), int(periods["latest_week"])
            )
            label = _format_week_label(int(periods["latest_week"]), int(periods["latest_week_year"]))
        elif range_mode == "Mes":
            start_date, end_date = _month_range_from_selection(
                int(periods["latest_month_year"]), int(periods["latest_month"])
            )
            label = _format_month_label(int(periods["latest_month"]), int(periods["latest_month_year"]))
        elif range_mode == "Año":
            start_date, end_date = _year_range_from_selection(int(periods["latest_year"]))
            label = _format_year_label(int(periods["latest_year"]))
        else:
            end_date = periods["max_date"]
            start_date = max(periods["min_date"], end_date - timedelta(days=29))
            label = f"{start_date.isoformat()} a {end_date.isoformat()}"
    else:
        if range_mode == "Semana":
            year = int(filters["period_week_year"])
            week = int(filters["period_week"])
            start_date, end_date = _week_range_from_selection(year, week)
            label = _format_week_label(week, year)
        elif range_mode == "Mes":
            year = int(filters["period_month_year"])
            month = int(filters["period_month"])
            start_date, end_date = _month_range_from_selection(year, month)
            label = _format_month_label(month, year)
        elif range_mode == "Año":
            year = int(filters["period_year"])
            start_date, end_date = _year_range_from_selection(year)
            label = _format_year_label(year)
        else:
            start_date = filters["date_start"]
            end_date = filters["date_end"]
            if isinstance(start_date, datetime):
                start_date = start_date.date()
            if isinstance(end_date, datetime):
                end_date = end_date.date()
            label = f"{start_date.isoformat()} a {end_date.isoformat()}"

    if start_date > end_date:
        start_date, end_date = end_date, start_date
        if range_mode == "Rango fechas":
            label = f"{start_date.isoformat()} a {end_date.isoformat()}"
        st.session_state["period_swap_warning"] = True
    else:
        st.session_state["period_swap_warning"] = False

    days_range = max(1, (end_date - start_date).days + 1)
    recommended = _recommended_granularity(days_range)
    adjusted_granularity = granularity_choice if granularity_choice != "Auto" else recommended

    notes: list[tuple[str, str]] = []
    if granularity_choice == "Auto":
        notes.append(("info", f"Granularidad auto ajustada a {recommended.lower()}."))
    if range_mode == "Semana" and adjusted_granularity not in {"Semanal", "Diario"}:
        adjusted_granularity = "Semanal"
        notes.append(("warning", "Granularidad ajustada a semanal para el rango semanal."))
    if range_mode == "Mes" and adjusted_granularity == "Anual":
        adjusted_granularity = "Mensual"
        notes.append(("warning", "Granularidad ajustada a mensual para el rango mensual."))
    if range_mode == "Mes" and adjusted_granularity == "Semanal":
        notes.append(("info", "Granularidad semanal aplicada dentro del mes seleccionado."))
    if granularity_choice not in {"Auto", adjusted_granularity}:
        notes.append(("warning", f"Granularidad ajustada a {adjusted_granularity.lower()} por el rango."))

    current_section = st.session_state.get("nav_section") or st.session_state.get("page_nav")
    if current_section == "Pedidos por Surtir" and adjusted_granularity != "Mensual":
        adjusted_granularity = "Mensual"
        notes.append(("info", "Pedidos por surtir se analiza con granularidad mensual."))

    st.session_state["period_notes"] = notes
    st.session_state["normalized_start_date"] = start_date
    st.session_state["normalized_end_date"] = end_date
    st.session_state["period_label"] = label
    st.session_state["normalized_granularity"] = adjusted_granularity

    return start_date, end_date, label, adjusted_granularity


def _recommended_granularity(days_range: int) -> str:
    if days_range < 45:
        return "Semanal"
    if days_range <= 400:
        return "Mensual"
    return "Anual"


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
    st.session_state.setdefault("period_mode", "Último periodo disponible")
    st.session_state.setdefault("range_mode", "Mes")
    st.session_state.setdefault("granularity", "Auto")
    st.session_state.setdefault("currency_view", "MXN")
    st.session_state.setdefault("period_year", periods["latest_year"])
    st.session_state.setdefault("period_month", periods["latest_month"])
    st.session_state.setdefault("period_month_year", periods["latest_month_year"])
    st.session_state.setdefault("period_week", periods["latest_week"])
    st.session_state.setdefault("period_week_year", periods["latest_week_year"])
    st.session_state.setdefault("date_start", periods["min_date"])
    st.session_state.setdefault("date_end", periods["max_date"])

    period_mode = st.sidebar.selectbox(
        "Periodo",
        ["Último periodo disponible", "Personalizado"],
        key="period_mode",
    )

    range_mode = st.sidebar.selectbox(
        "Rango",
        ["Semana", "Mes", "Rango fechas", "Año"],
        key="range_mode",
    )

    currency_view = st.sidebar.selectbox(
        "Moneda",
        ["MXN", "USD"],
        key="currency_view",
    )

    granularity_choice = st.sidebar.selectbox(
        "Granularidad",
        ["Auto", "Diario", "Semanal", "Mensual", "Anual"],
        key="granularity",
    )

    if st.sidebar.button("Actualizar ahora", key="refresh_now"):
        refreshed_at = datetime.now()
        st.session_state["last_refresh_at"] = refreshed_at
        st.toast(f"Datos actualizados (simulación) – {refreshed_at:%d/%m/%Y %H:%M}")

    last_refresh = st.session_state.get("last_refresh_at")
    if last_refresh:
        st.sidebar.caption(f"Última actualización: {last_refresh:%d/%m/%Y %H:%M}")
    else:
        st.sidebar.caption("Última actualización: pendiente")

    if period_mode == "Personalizado":
        if range_mode == "Semana":
            year = st.sidebar.selectbox("Año", periods["years"], key="period_week_year")
            weeks = periods["weeks_by_year"].get(int(year), [periods["latest_week"]])
            if st.session_state.get("period_week") not in weeks:
                st.session_state["period_week"] = weeks[-1]
            st.sidebar.selectbox(
                "Semana",
                weeks,
                key="period_week",
                format_func=lambda value, selected_year=int(year): _format_week_label(
                    int(value), int(selected_year)
                ),
            )
        elif range_mode == "Mes":
            year = st.sidebar.selectbox("Año", periods["years"], key="period_month_year")
            months = periods["months_by_year"].get(int(year), [periods["latest_month"]])
            if st.session_state.get("period_month") not in months:
                st.session_state["period_month"] = months[-1]
            st.sidebar.selectbox(
                "Mes",
                months,
                format_func=lambda value, selected_year=int(year): _format_month_label(
                    int(value), int(selected_year)
                ),
                key="period_month",
            )
        elif range_mode == "Año":
            st.sidebar.selectbox(
                "Año",
                periods["years"],
                key="period_year",
                format_func=_format_year_label,
            )
        else:
            date_start, date_end = st.sidebar.date_input(
                "Rango",
                value=(st.session_state["date_start"], st.session_state["date_end"]),
                min_value=periods["min_date"],
                max_value=periods["max_date"],
            )
            st.session_state["date_start"] = date_start
            st.session_state["date_end"] = date_end

    start_date, end_date, label, granularity = normalize_period(
        {
            "period_mode": period_mode,
            "range_mode": range_mode,
            "granularity": granularity_choice,
            "period_week_year": st.session_state["period_week_year"],
            "period_week": st.session_state["period_week"],
            "period_month_year": st.session_state["period_month_year"],
            "period_month": st.session_state["period_month"],
            "period_year": st.session_state["period_year"],
            "date_start": st.session_state["date_start"],
            "date_end": st.session_state["date_end"],
        },
        periods,
    )

    if st.session_state.get("period_swap_warning"):
        st.sidebar.warning("La fecha de inicio era mayor que la final; se ajustó automáticamente.")

    notes = st.session_state.get("period_notes", [])
    for level, message in notes:
        if level == "warning":
            st.sidebar.warning(message)
        else:
            st.sidebar.info(message)

    st.sidebar.caption(f"Periodo: {label}")
    st.sidebar.caption(f"Del: {start_date.isoformat()}  Al: {end_date.isoformat()}")

    return {
        "start_date": start_date,
        "end_date": end_date,
        "granularity": granularity,
        "currency_view": currency_view,
        "period_mode": period_mode,
        "range_mode": range_mode,
        "period_label": label,
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

    with perf_logger("apply_sales_filters"):
        sales_filtered = cached_apply_sales_filters(
            ventas_normalized,
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
            filter_key,
        )

    pedidos_filtered = None
    if pedidos is not None and not pedidos.empty:
        with perf_logger("apply_order_filters"):
            pedidos_filtered = cached_apply_order_filters(
                pedidos,
                global_filters["start_date"],
                global_filters["end_date"],
                vendors,
                sale_origins,
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
        period_mode=str(global_filters["period_mode"]),
        range_mode=str(global_filters["range_mode"]),
        period_label=str(global_filters["period_label"]),
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
        clients=bundle.clientes.copy() if bundle.clientes is not None else pd.DataFrame(),
        products=bundle.productos.copy() if bundle.productos is not None else pd.DataFrame(),
        pedidos=pedidos_filtered,
        currency_label=currency_label,
        revenue_column=revenue_column,
        unit_price_column=unit_price_column,
        fx_average=fx_average,
        filter_key=filter_key,
    )

    ventas_filtrado, clientes_filtrado, productos_filtrado, pedidos_filtrado = apply_global_filters(
        bundle,
        filter_state,
    )

    filter_state.sales = ventas_filtrado
    filter_state.clients = clientes_filtrado
    filter_state.products = productos_filtrado
    filter_state.pedidos = pedidos_filtrado

    return filter_state
