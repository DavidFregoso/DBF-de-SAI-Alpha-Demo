from __future__ import annotations

from io import BytesIO
from pathlib import Path
import importlib.util

import pandas as pd
import plotly.io as pio
import streamlit as st

from sai_alpha.etl import DataBundle, enrich_pedidos, enrich_sales, load_data, resolve_dbf_dir
from sai_alpha.formatting import fmt_int, fmt_money

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


@st.cache_data(show_spinner=False)
def load_bundle() -> DataBundle:
    return load_data(DATA_DIR)


@st.cache_data(show_spinner=False)
def load_sales() -> pd.DataFrame:
    bundle = load_bundle()
    ventas = enrich_sales(bundle)
    if not ventas.empty and "SALE_DATE" in ventas.columns:
        ventas["SALE_DATE"] = pd.to_datetime(ventas["SALE_DATE"], errors="coerce")
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
    "SELLER_NAME",
    "QTY",
    "REVENUE_MXN",
    "REVENUE_USD",
}


def validate_sales_schema(ventas: pd.DataFrame) -> list[str]:
    return sorted(REQUIRED_SALES_COLUMNS - set(ventas.columns))


def apply_theme() -> None:
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
            [data-testid="stSidebarNav"],
            [data-testid="stSidebarNavItems"],
            [data-testid="stSidebarNavSeparator"] {{
                display: none;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.session_state["plotly_colors"] = [accent, primary, "#2c3e50", "#6f42c1", "#fd7e14"]
    pio.templates["sai_alpha"] = dict(
        layout=dict(
            colorway=st.session_state["plotly_colors"],
            font=dict(family="Inter, sans-serif"),
            hovermode="x unified",
        )
    )
    pio.templates.default = "sai_alpha"


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


def export_dataframe(df: pd.DataFrame) -> tuple[bytes, str, str] | None:
    engines = [
        engine
        for engine in ("xlsxwriter", "openpyxl")
        if importlib.util.find_spec(engine) is not None
    ]
    if not engines:
        return None
    for engine in engines:
        buffer = BytesIO()
        try:
            with pd.ExcelWriter(buffer, engine=engine) as writer:
                df.to_excel(writer, index=False)
            return (
                buffer.getvalue(),
                "xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except Exception:
            continue
    return None


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
        st.caption(
            "Exportación Excel no disponible. Se descargará CSV únicamente "
            "(instala xlsxwriter u openpyxl si necesitas Excel)."
        )
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
        df["REVENUE_MXN"] = pd.to_numeric(df["AMOUNT_MXN"], errors="coerce").fillna(0)
    if "REVENUE_MXN" not in df.columns:
        df["REVENUE_MXN"] = pd.to_numeric(df.get("TOTAL_MXN", 0), errors="coerce").fillna(0)
    if "REVENUE_USD" not in df.columns and "AMOUNT_USD" in df.columns:
        df["REVENUE_USD"] = pd.to_numeric(df["AMOUNT_USD"], errors="coerce").fillna(0)
    if "REVENUE_USD" not in df.columns and "USD_MXN_RATE" in df.columns:
        df["REVENUE_USD"] = df["REVENUE_MXN"] / df["USD_MXN_RATE"].replace(0, pd.NA)
    if "UNIT_PRICE_MXN" in df.columns and "UNIT_PRICE_USD" not in df.columns:
        if "USD_MXN_RATE" in df.columns:
            df["UNIT_PRICE_USD"] = df["UNIT_PRICE_MXN"] / df["USD_MXN_RATE"].replace(0, pd.NA)
        else:
            df["UNIT_PRICE_USD"] = df["UNIT_PRICE_MXN"]

    revenue_col, unit_col, label = _metric_columns(currency_mode)
    return df, revenue_col, unit_col, label


def format_currency_column(label: str) -> st.column_config.Column:
    return st.column_config.TextColumn(label)


def format_integer_column(label: str) -> st.column_config.Column:
    return st.column_config.TextColumn(label)


def format_number_column(label: str) -> st.column_config.Column:
    return st.column_config.TextColumn(label)


def format_money(value: float, currency: str = "MXN") -> str:
    return fmt_money(value, currency)


def format_int(value: float | int) -> str:
    return fmt_int(value)


def render_page_header(section_title: str, subtitle: str = "Abarrotes / Bebidas / Botanas / Lácteos") -> None:
    st.markdown("<div class='app-header'>Demo Tienda – Dashboard Ejecutivo</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='app-subtitle'>{subtitle}</div>", unsafe_allow_html=True)
    st.title(section_title)


@st.cache_data(show_spinner=False)
def build_time_series(df: pd.DataFrame, date_col: str, value_col: str, granularity: str) -> pd.DataFrame:
    if df.empty or date_col not in df.columns or value_col not in df.columns:
        return pd.DataFrame({date_col: [], value_col: []})
    if granularity == "Diario":
        series = df.groupby(df[date_col].dt.date)[value_col].sum().reset_index(name=value_col)
        series[date_col] = pd.to_datetime(series[date_col])
        return series
    if granularity == "Semanal":
        return df.groupby(pd.Grouper(key=date_col, freq="W-MON"))[value_col].sum().reset_index()
    if granularity == "Mensual":
        return df.groupby(pd.Grouper(key=date_col, freq="M"))[value_col].sum().reset_index()
    return df.groupby(pd.Grouper(key=date_col, freq="Y"))[value_col].sum().reset_index()


def table_height(rows: int) -> int:
    row_height = int(st.session_state.get("row_height", 34))
    return min(600, max(220, (rows + 1) * row_height))
