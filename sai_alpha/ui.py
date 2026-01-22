from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path
import importlib.util

import pandas as pd
import streamlit as st

from sai_alpha.etl import DataBundle, enrich_pedidos, enrich_sales, load_data, resolve_dbf_dir

DATA_DIR = resolve_dbf_dir()
EXPORT_DIR = Path("data/exports")


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
    invoice_types: list[str]
    order_types: list[str]
    order_statuses: list[str] | None
    sales: pd.DataFrame
    pedidos: pd.DataFrame | None
    currency_label: str
    revenue_column: str
    unit_price_column: str


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


def init_session_state() -> None:
    defaults = {
        "theme_primary": "#0f5132",
        "theme_accent": "#198754",
        "table_density": "Confortable",
        "default_window_days": 90,
        "date_preset": "Rango personalizado",
        "granularity": "Mensual",
        "currency_mode": "Normalizado a MXN",
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
    if currency_mode == "Ver en USD":
        return "REVENUE_USD", "UNIT_PRICE_USD", "USD"
    if currency_mode == "Ver en MXN":
        return "REVENUE_MXN", "UNIT_PRICE", "MXN"
    return "REVENUE_NORM_MXN", "UNIT_PRICE", "MXN"


def normalize_currency(ventas: pd.DataFrame, currency_mode: str) -> tuple[pd.DataFrame, str, str, str]:
    df = ventas.copy()
    df["REVENUE_MXN"] = df["REVENUE"].astype(float)
    if "REVENUE_USD" not in df.columns and "TC_MXN_USD" in df.columns:
        df["REVENUE_USD"] = df["REVENUE_MXN"] / df["TC_MXN_USD"].replace(0, pd.NA)
    if "REVENUE_USD" in df.columns:
        df["REVENUE_USD"] = df["REVENUE_USD"].astype(float)
    if "TC_MXN_USD" in df.columns:
        df["REVENUE_NORM_MXN"] = df.apply(
            lambda row: row["REVENUE_USD"] * row["TC_MXN_USD"]
            if row.get("MONEDA") == "USD"
            else row["REVENUE_MXN"],
            axis=1,
        )
    else:
        df["REVENUE_NORM_MXN"] = df["REVENUE_MXN"]
    if "TC_MXN_USD" in df.columns:
        df["UNIT_PRICE_USD"] = df["UNIT_PRICE"] / df["TC_MXN_USD"].replace(0, pd.NA)
    else:
        df["UNIT_PRICE_USD"] = df["UNIT_PRICE"]

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


def render_sidebar_filters(ventas: pd.DataFrame, pedidos: pd.DataFrame | None) -> FilterState:
    init_session_state()
    st.sidebar.markdown("## Dashboard Ejecutivo SAI Alpha (Demo)")
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

    if preset == "Rango personalizado":
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
    else:
        start_date, end_date = _date_range_from_preset(preset, max_date)

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
        ["Ver en MXN", "Ver en USD", "Normalizado a MXN"],
        index=["Ver en MXN", "Ver en USD", "Normalizado a MXN"].index(
            st.session_state.get("currency_mode", "Normalizado a MXN")
        ),
        key="currency_mode",
    )

    brand_options = sorted(ventas["BRAND"].dropna().unique().tolist())
    category_options = sorted(ventas["CATEGORY"].dropna().unique().tolist())
    vendor_options = sorted(ventas["VENDOR_NAME"].dropna().unique().tolist())
    sale_origin_options = sorted(ventas["ORIGEN_VTA"].dropna().unique().tolist())
    client_origin_options = sorted(ventas["ORIGEN_CLI"].dropna().unique().tolist())
    invoice_options = sorted(ventas["TIPO_FACT"].dropna().unique().tolist())
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
        invoice_types=invoice_types,
        order_types=order_types,
        order_statuses=order_statuses,
        sales=sales_filtered,
        pedidos=pedidos_filtered,
        currency_label=currency_label,
        revenue_column=revenue_column,
        unit_price_column=unit_price_column,
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
        df = df[df["VENDOR_NAME"].isin(vendors)]
    else:
        return df.iloc[0:0]
    if sale_origins:
        df = df[df["ORIGEN_VTA"].isin(sale_origins)]
    else:
        return df.iloc[0:0]
    if client_origins:
        df = df[df["ORIGEN_CLI"].isin(client_origins)]
    else:
        return df.iloc[0:0]
    if invoice_types:
        df = df[df["TIPO_FACT"].isin(invoice_types)]
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
    if vendors and "VENDOR_NAME" in df.columns:
        df = df[df["VENDOR_NAME"].isin(vendors)]
    elif vendors == [] and "VENDOR_NAME" in df.columns:
        return df.iloc[0:0]
    if sale_origins and "ORIGEN_VTA" in df.columns:
        df = df[df["ORIGEN_VTA"].isin(sale_origins)]
    elif sale_origins == [] and "ORIGEN_VTA" in df.columns:
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


def build_time_series(df: pd.DataFrame, date_col: str, value_col: str, granularity: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame({date_col: [], value_col: []})
    if granularity == "Diario":
        series = df.groupby(df[date_col].dt.date)[value_col].sum().reset_index(name=value_col)
        series[date_col] = pd.to_datetime(series[date_col])
        return series
    if granularity == "Semanal":
        series = df.groupby(pd.Grouper(key=date_col, freq="W"))[value_col].sum().reset_index()
        return series
    if granularity == "Mensual":
        series = df.groupby(pd.Grouper(key=date_col, freq="M"))[value_col].sum().reset_index()
        return series
    series = df.groupby(pd.Grouper(key=date_col, freq="Y"))[value_col].sum().reset_index()
    return series


def table_height(rows: int) -> int:
    row_height = int(st.session_state.get("row_height", 34))
    return min(600, max(220, (rows + 1) * row_height))
