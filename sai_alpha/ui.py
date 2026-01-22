from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
import calendar
from io import BytesIO
from pathlib import Path
import importlib.util

import pandas as pd
import streamlit as st

from sai_alpha.etl import DataBundle, enrich_pedidos, enrich_sales, load_data, resolve_dbf_dir

DATA_DIR = resolve_dbf_dir()
EXPORT_DIR = Path("data/exports")

PAGE_ROUTES = {
    "Resumen Ejecutivo": "pages/1_Resumen Ejecutivo.py",
    "Clientes": "pages/2_Clientes.py",
    "Vendedores": "pages/3_Vendedores.py",
    "Productos": "pages/4_Productos.py",
    "Pedidos por Surtir": "pages/5_Pedidos por Surtir.py",
    "Configuración": "pages/6_Configuración.py",
}


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


@st.cache_data(show_spinner=False)
def load_bundle() -> DataBundle:
    return load_data(DATA_DIR)


@st.cache_data(show_spinner=False)
def load_sales() -> pd.DataFrame:
    bundle = load_bundle()
    ventas = enrich_sales(bundle)
    ventas["SALE_DATE"] = pd.to_datetime(ventas["SALE_DATE"])
    if "LAST_PURCHASE" in ventas.columns:
        ventas["LAST_PURCHASE"] = pd.to_datetime(ventas["LAST_PURCHASE"])
    return ventas


@st.cache_data(show_spinner=False)
def load_orders() -> pd.DataFrame:
    bundle = load_bundle()
    pedidos = enrich_pedidos(bundle)
    if not pedidos.empty and "ORDER_DATE" in pedidos.columns:
        pedidos["ORDER_DATE"] = pd.to_datetime(pedidos["ORDER_DATE"])
    return pedidos


REQUIRED_SALES_COLUMNS = {
    "SALE_DATE",
    "PRODUCT_ID",
    "PRODUCT_NAME",
    "BRAND",
    "CATEGORY",
    "CLIENT_ID",
    "CLIENT_NAME",
    "CLIENT_ORIGIN",
    "SELLER_ID",
    "SELLER_NAME",
    "ORIGEN_VENTA",
    "RECOMM_SOURCE",
    "TIPO_FACTURA",
    "TIPO_ORDEN",
    "STATUS",
    "QTY",
    "UNIT_PRICE_MXN",
    "REVENUE_MXN",
    "REVENUE_USD",
}


def validate_sales_schema(ventas: pd.DataFrame) -> list[str]:
    missing = sorted(REQUIRED_SALES_COLUMNS - set(ventas.columns))
    return missing


def init_session_state() -> None:
    defaults = {
        "theme_primary": "#0f5132",
        "theme_accent": "#198754",
        "table_density": "Confortable",
        "default_window_days": 90,
        "date_preset": "Semana",
        "granularity": "Semanal",
        "currency_mode": "MXN",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def apply_theme() -> None:
    init_session_state()
    primary = st.session_state.get("theme_primary", "#0f5132")
    accent = st.session_state.get("theme_accent", "#198754")
    density = st.session_state.get("table_density", "Confortable")
    row_height = {"Compacta": 26, "Confortable": 34, "Amplia": 42}.get(density, 34)
    st.session_state["row_height"] = row_height

    st.markdown(
        f"""
        <style>
            .app-header {{
                font-weight: 700;
                font-size: 1.6rem;
                color: {primary};
                margin-bottom: 0.25rem;
            }}
            .app-subtitle {{
                color: #6c757d;
                margin-top: 0;
            }}
            [data-testid="stMetricValue"] {{
                color: {primary};
            }}
            [data-testid="stMetricDelta"] {{
                color: {accent};
            }}
            .section-title {{
                border-left: 4px solid {accent};
                padding-left: 0.6rem;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.session_state["plotly_colors"] = [accent, primary, "#2c3e50", "#6f42c1", "#fd7e14"]


def render_page_nav(current_page: str) -> None:
    pages = list(PAGE_ROUTES.keys())
    try:
        current_index = pages.index(current_page)
    except ValueError:
        current_index = 0
    selection = st.sidebar.selectbox(
        "Ir a página",
        pages,
        index=current_index,
        key="page_nav",
    )
    if selection != current_page:
        st.switch_page(PAGE_ROUTES[selection])


def plotly_colors() -> list[str]:
    return st.session_state.get("plotly_colors", ["#198754", "#0f5132", "#2c3e50"])


def _resolve_excel_engine() -> str | None:
    if importlib.util.find_spec("xlsxwriter") is not None:
        return "xlsxwriter"
    if importlib.util.find_spec("openpyxl") is not None:
        return "openpyxl"
    return None


def export_dataframe(df: pd.DataFrame) -> tuple[bytes, str, str] | None:
    engine = _resolve_excel_engine()
    if engine is None:
        return None
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine=engine) as writer:
        df.to_excel(writer, index=False)
    return (
        buffer.getvalue(),
        "xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def export_buttons(df: pd.DataFrame, label: str) -> None:
    csv_data = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=f"Descargar {label} CSV",
        data=csv_data,
        file_name=f"{label}.csv",
        mime="text/csv",
    )

    excel_export = export_dataframe(df)
    if excel_export is None:
        st.caption("Exportación Excel no disponible (instala xlsxwriter u openpyxl).")
        return

    data, extension, mime = excel_export
    st.download_button(
        label=f"Descargar {label} Excel",
        data=data,
        file_name=f"{label}.{extension}",
        mime=mime,
    )


def _metric_columns(currency_mode: str) -> tuple[str, str, str]:
    if currency_mode == "USD":
        return "REVENUE_USD", "UNIT_PRICE_USD", "USD"
    return "REVENUE_MXN", "UNIT_PRICE_MXN", "MXN"


@st.cache_data(show_spinner=False)
def normalize_currency(ventas: pd.DataFrame, currency_mode: str) -> tuple[pd.DataFrame, str, str, str]:
    df = ventas.copy()
    if "REVENUE_MXN" not in df.columns and "AMOUNT_MXN" in df.columns:
        df["REVENUE_MXN"] = df["AMOUNT_MXN"].astype(float)
    if "REVENUE_USD" not in df.columns and "AMOUNT_USD" in df.columns:
        df["REVENUE_USD"] = df["AMOUNT_USD"].astype(float)
    if "REVENUE_USD" not in df.columns and "USD_MXN_RATE" in df.columns:
        df["REVENUE_USD"] = df["REVENUE_MXN"] / df["USD_MXN_RATE"].replace(0, pd.NA)
    if "UNIT_PRICE_MXN" in df.columns and "UNIT_PRICE_USD" not in df.columns:
        if "USD_MXN_RATE" in df.columns:
            df["UNIT_PRICE_USD"] = df["UNIT_PRICE_MXN"] / df["USD_MXN_RATE"].replace(0, pd.NA)
        else:
            df["UNIT_PRICE_USD"] = df["UNIT_PRICE_MXN"]

    revenue_col, unit_col, label = _metric_columns(currency_mode)
    return df, revenue_col, unit_col, label


def _init_multiselect_state(key: str, options: list[str], default: list[str]) -> None:
    if key not in st.session_state:
        st.session_state[key] = default
    else:
        current = st.session_state[key]
        if not current:
            return
        missing = [value for value in current if value not in options]
        if missing:
            st.session_state[key] = [value for value in current if value in options]


def multiselect_with_actions(label: str, options: list[str], key: str) -> list[str]:
    _init_multiselect_state(key, options, options)
    col1, col2 = st.sidebar.columns(2)
    if col1.button("Seleccionar todo", key=f"{key}_all"):
        st.session_state[key] = options
        st.rerun()
    if col2.button("Limpiar", key=f"{key}_clear"):
        st.session_state[key] = []
        st.rerun()
    return st.sidebar.multiselect(label, options, key=key)


def _resolve_date_range(max_date: date) -> tuple[date, date]:
    default_days = int(st.session_state.get("default_window_days", 90))
    start_default = max_date - timedelta(days=default_days - 1)
    return start_default, max_date


def _date_range_from_preset(preset: str, max_date: date) -> tuple[date, date]:
    if preset == "Día":
        return max_date, max_date
    if preset == "Semana":
        return max_date - timedelta(days=6), max_date
    if preset == "Mes":
        return max_date - timedelta(days=29), max_date
    if preset == "Año":
        return max_date - timedelta(days=364), max_date
    return _resolve_date_range(max_date)


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


def render_sidebar_filters(ventas: pd.DataFrame, pedidos: pd.DataFrame | None) -> FilterState:
    init_session_state()
    logo_path = Path("assets") / "logo.svg"
    if logo_path.exists():
        st.sidebar.image(str(logo_path), use_column_width=True)
    st.sidebar.markdown("## Demo Tienda – Dashboard Ejecutivo")
    st.sidebar.caption("Filtros globales")

    min_date = ventas["SALE_DATE"].min().date()
    max_date = ventas["SALE_DATE"].max().date()

    preset = st.sidebar.selectbox(
        "Periodo",
        ["Día", "Semana", "Mes", "Año", "Rango personalizado"],
        index=["Día", "Semana", "Mes", "Año", "Rango personalizado"].index(
            st.session_state.get("date_preset", "Rango personalizado")
        ),
        key="date_preset",
    )

    if preset == "Semana":
        years = sorted(ventas["SALE_DATE"].dt.year.unique().tolist())
        default_year = st.session_state.get("period_year", max_date.year)
        year = st.sidebar.selectbox("Año", years, index=years.index(default_year), key="period_year")
        weeks = sorted(
            ventas[ventas["SALE_DATE"].dt.year == year]["SALE_DATE"].dt.isocalendar().week.unique().tolist()
        )
        default_week = int(max_date.isocalendar().week) if year == max_date.year else weeks[-1]
        week = st.sidebar.selectbox("Semana", weeks, index=weeks.index(default_week), key="period_week")
        start_date, end_date = _week_range_from_selection(year, int(week))
    elif preset == "Mes":
        years = sorted(ventas["SALE_DATE"].dt.year.unique().tolist())
        default_year = st.session_state.get("period_month_year", max_date.year)
        year = st.sidebar.selectbox(
            "Año",
            years,
            index=years.index(default_year),
            key="period_month_year",
        )
        month_names = [calendar.month_name[m] for m in range(1, 13)]
        default_month_state = st.session_state.get("period_month", max_date.month)
        if isinstance(default_month_state, str):
            default_month_name = default_month_state
        else:
            default_month_name = calendar.month_name[int(default_month_state)]
        month_name = st.sidebar.selectbox(
            "Mes",
            month_names,
            index=month_names.index(default_month_name),
            key="period_month",
        )
        month = month_names.index(month_name) + 1
        start_date, end_date = _month_range_from_selection(year, month)
    elif preset == "Año":
        years = sorted(ventas["SALE_DATE"].dt.year.unique().tolist())
        default_year = st.session_state.get("period_year_only", max_date.year)
        year = st.sidebar.selectbox(
            "Año",
            years,
            index=years.index(default_year),
            key="period_year_only",
        )
        start_date, end_date = _year_range_from_selection(year)
    elif preset == "Día":
        start_date, end_date = max_date, max_date
    else:
        start_default, end_default = _resolve_date_range(max_date)
        date_range = st.sidebar.date_input(
            "Rango de fechas",
            value=(start_default, end_default),
            min_value=min_date,
            max_value=max_date,
        )
        if isinstance(date_range, tuple):
            start_date, end_date = date_range
        else:
            start_date, end_date = start_default, end_default

    if start_date < min_date:
        start_date = min_date
    if end_date > max_date:
        end_date = max_date

    granularity = st.sidebar.selectbox(
        "Granularidad",
        ["Diario", "Semanal", "Mensual", "Anual"],
        index=["Diario", "Semanal", "Mensual", "Anual"].index(
            st.session_state.get("granularity", "Mensual")
        ),
        key="granularity",
    )

    currency_mode = st.sidebar.radio(
        "Vista moneda",
        ["MXN", "USD"],
        index=["MXN", "USD"].index(st.session_state.get("currency_mode", "MXN")),
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
        order_statuses = multiselect_with_actions("Estatus de pedido", status_options, "filter_order_statuses")
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

    with st.sidebar.expander("Tema", expanded=False):
        st.color_picker("Color primario", key="theme_primary")
        st.color_picker("Color acento", key="theme_accent")
        st.selectbox(
            "Densidad de tablas",
            ["Compacta", "Confortable", "Amplia"],
            key="table_density",
        )

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


@st.cache_data(show_spinner=False)
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


@st.cache_data(show_spinner=False)
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


def format_currency_column(label: str) -> st.column_config.Column:
    return st.column_config.NumberColumn(label, format="$ %,.2f")


def format_integer_column(label: str) -> st.column_config.Column:
    return st.column_config.NumberColumn(label, format="%,d")


def format_number_column(label: str) -> st.column_config.Column:
    return st.column_config.NumberColumn(label, format="%,.2f")


@st.cache_data(show_spinner=False)
def build_time_series(df: pd.DataFrame, date_col: str, value_col: str, granularity: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame({date_col: [], value_col: []})
    if granularity == "Diario":
        series = df.groupby(df[date_col].dt.date)[value_col].sum().reset_index(name=value_col)
        series[date_col] = pd.to_datetime(series[date_col])
        return series
    if granularity == "Semanal":
        series = df.groupby(pd.Grouper(key=date_col, freq="W-MON"))[value_col].sum().reset_index()
        return series
    if granularity == "Mensual":
        series = df.groupby(pd.Grouper(key=date_col, freq="M"))[value_col].sum().reset_index()
        return series
    series = df.groupby(pd.Grouper(key=date_col, freq="Y"))[value_col].sum().reset_index()
    return series


def table_height(rows: int) -> int:
    row_height = int(st.session_state.get("row_height", 34))
    return min(600, max(220, (rows + 1) * row_height))
