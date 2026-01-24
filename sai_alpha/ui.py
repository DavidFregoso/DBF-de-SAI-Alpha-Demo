from __future__ import annotations

from io import BytesIO
from datetime import datetime
from pathlib import Path
import importlib.util

import pandas as pd
import streamlit as st

from sai_alpha import normalize as normalize_utils
from sai_alpha.etl import DataBundle, enrich_pedidos, enrich_sales, load_data, resolve_dbf_dir
from sai_alpha.formatting import fmt_int, fmt_money
from sai_alpha.theme import apply_global_css, apply_plotly_theme, get_theme_config
from sai_alpha.schema import DEFAULT_TEXT

DATA_DIR = resolve_dbf_dir()
EXPORT_DIR = Path("data/exports")

PAGE_ROUTES = {
    "Configuración": "pages/6_Configuración.py",
    "Resumen Ejecutivo": "pages/1_Resumen Ejecutivo.py",
    "Clientes": "pages/2_Clientes.py",
    "Vendedores": "pages/3_Vendedores.py",
    "Productos": "pages/4_Productos.py",
    "Pedidos por Surtir": "pages/5_Pedidos por Surtir.py",
}

THEME_QUERY_MAP = {
    "Claro": "light",
    "Oscuro": "dark",
}

THEME_QUERY_REVERSE = {
    "light": "Claro",
    "claro": "Claro",
    "dark": "Oscuro",
    "oscuro": "Oscuro",
}


def init_theme_state() -> None:
    if "theme" not in st.session_state:
        st.session_state["theme"] = "Oscuro"
    if "theme_source" not in st.session_state:
        st.session_state["theme_source"] = "session"

    theme_param = st.query_params.get("theme")
    if isinstance(theme_param, list):
        theme_param = theme_param[0] if theme_param else None
    if isinstance(theme_param, str):
        normalized = theme_param.strip().lower()
        if normalized in THEME_QUERY_REVERSE:
            st.session_state["theme"] = THEME_QUERY_REVERSE[normalized]
            st.session_state["theme_source"] = "query"

    desired_param = THEME_QUERY_MAP.get(st.session_state.get("theme"))
    if desired_param and st.query_params.get("theme") != desired_param:
        st.query_params["theme"] = desired_param


def apply_theme_css(theme_name: str) -> None:
    density = st.session_state.get("table_density", "Confortable")
    st.session_state["sidebar_header_rendered"] = False
    row_height = {"Compacta": 26, "Confortable": 34, "Amplia": 42}.get(density, 34)
    st.session_state["row_height"] = row_height
    theme_cfg = get_theme_config(theme_name)
    st.session_state["theme_cfg"] = theme_cfg
    st.session_state["plotly_colors"] = theme_cfg["palette"]
    apply_global_css(theme_cfg)
    apply_plotly_theme(theme_cfg)


@st.cache_data(show_spinner=False)
def load_bundle() -> DataBundle:
    bundle = load_data(DATA_DIR)
    return validate_bundle(bundle)


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


def record_schema_message(message: str) -> None:
    messages = st.session_state.setdefault("schema_messages", [])
    if message in messages:
        return
    messages.append(message)


def get_schema_messages() -> list[str]:
    return list(st.session_state.get("schema_messages", []))


def notify_once(key: str, message: str, level: str = "warning") -> None:
    seen = st.session_state.setdefault("notifications_seen", set())
    if key in seen:
        return
    seen.add(key)
    notifier = getattr(st, level, st.info)
    notifier(message)


def validate_bundle(bundle: DataBundle) -> DataBundle:
    ventas = bundle.ventas.copy()
    productos = bundle.productos.copy()
    pedidos = bundle.pedidos.copy() if bundle.pedidos is not None else None

    ventas_required = {"SALE_DATE", "PRODUCT_ID", "PRODUCT_NAME", "QTY", "REVENUE_MXN", "REVENUE_USD"}
    productos_required = {"PRODUCT_ID", "PRODUCT_NAME", "STOCK_QTY", "COST_MXN", "PRICE_MXN"}
    pedidos_required = {"ORDER_DATE", "PRODUCT_ID", "QTY_PENDING", "PRICE_MXN", "STATUS"}

    ventas_missing = sorted(ventas_required - set(ventas.columns))
    if ventas_missing:
        record_schema_message(
            "Se agregaron columnas faltantes en ventas.dbf: " + ", ".join(ventas_missing),
        )
    ventas = normalize_utils.ensure_columns(
        ventas,
        {
            "SALE_DATE": pd.NaT,
            "PRODUCT_ID": "",
            "PRODUCT_NAME": DEFAULT_TEXT,
            "QTY": 0,
            "REVENUE_MXN": 0,
            "REVENUE_USD": 0,
        },
    )

    productos_missing = sorted(productos_required - set(productos.columns))
    if productos_missing:
        record_schema_message(
            "Se agregaron columnas faltantes en productos.dbf: " + ", ".join(productos_missing),
        )
    productos = normalize_utils.ensure_columns(
        productos,
        {
            "PRODUCT_ID": "",
            "PRODUCT_NAME": DEFAULT_TEXT,
            "STOCK_QTY": 0,
            "COST_MXN": 0,
            "PRICE_MXN": 0,
        },
    )

    if pedidos is not None:
        pedidos_missing = sorted(pedidos_required - set(pedidos.columns))
        if pedidos_missing:
            record_schema_message(
                "Se agregaron columnas faltantes en pedidos.dbf: " + ", ".join(pedidos_missing),
            )
        pedidos = normalize_utils.ensure_columns(
            pedidos,
            {
                "ORDER_DATE": pd.NaT,
                "PRODUCT_ID": "",
                "QTY_PENDING": 0,
                "PRICE_MXN": 0,
                "STATUS": "Pendiente",
            },
        )

    return DataBundle(
        ventas=ventas,
        productos=productos,
        clientes=bundle.clientes,
        vendedores=bundle.vendedores,
        tipo_cambio=bundle.tipo_cambio,
        facturas=bundle.facturas,
        notas_credito=bundle.notas_credito,
        pedidos=pedidos,
    )


def apply_theme() -> None:
    theme_mode = st.session_state.get("theme", st.session_state.get("theme_mode", "Claro"))
    apply_theme_css(theme_mode)


def render_page_nav(current_page: str) -> None:
    pages = list(PAGE_ROUTES.keys())
    try:
        current_index = pages.index(current_page)
    except ValueError:
        current_index = 0
    render_sidebar_header()
    selection = st.sidebar.selectbox(
        "Ir a página",
        pages,
        index=current_index,
        key="page_nav",
    )
    if selection != current_page:
        st.switch_page(PAGE_ROUTES[selection])


def init_session_state() -> None:
    from sai_alpha.state import init_state_once

    init_state_once(load_sales())


def render_sidebar_header() -> None:
    if st.session_state.get("sidebar_header_rendered"):
        return
    st.sidebar.markdown("<div class='sidebar-title'>Demo Surtidora de Abarrotes</div>", unsafe_allow_html=True)
    st.sidebar.markdown("<div class='sidebar-subtitle'>Dashboard Ejecutivo</div>", unsafe_allow_html=True)
    st.session_state["sidebar_header_rendered"] = True


def reset_theme_defaults() -> None:
    st.session_state["theme_primary"] = "#0f5132"
    st.session_state["theme_accent"] = "#198754"
    st.session_state["theme"] = "Claro"
    st.session_state["table_density"] = "Confortable"


def render_sidebar_filters(ventas: pd.DataFrame, pedidos: pd.DataFrame | None) -> object:
    from sai_alpha.filters import AdvancedFilterContext, build_advanced_filters, build_filter_state, build_global_filters

    init_session_state()
    render_sidebar_header()
    with st.sidebar.expander("Filtros globales", expanded=True):
        global_filters = build_global_filters(ventas)

    with st.sidebar.expander("Filtros avanzados", expanded=False) as expander:
        advanced_context = AdvancedFilterContext(
            brands=True,
            categories=True,
            vendors=True,
            sale_origins=True,
            client_origins=True,
            recommendation_sources=True,
            invoice_types=True,
            order_types=True,
            order_statuses=pedidos is not None and not pedidos.empty,
        )
        advanced_filters = build_advanced_filters(ventas, pedidos, advanced_context, expander)

    bundle = load_bundle()
    return build_filter_state(ventas, pedidos, bundle, global_filters, advanced_filters)


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


def render_page_header(section_title: str, subtitle: str = "Dashboard Ejecutivo") -> None:
    st.markdown(f"<div class='section-title'>{section_title}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='app-subtitle'>{subtitle}</div>", unsafe_allow_html=True)


def render_app_header(period_label: str, currency_label: str, last_update: datetime | None) -> None:
    last_update_display = last_update.strftime("%d/%m/%Y %H:%M") if last_update else "Sin datos"
    container = st.container()
    with container:
        col_left, col_right = st.columns([0.75, 0.25])
        with col_left:
            st.markdown(
                """
                <div class="top-header">
                    <div>
                        <div class="top-header-title">Demo Surtidora de Abarrotes</div>
                        <div class="top-header-sub">Dashboard Ejecutivo</div>
                    </div>
                    <div class="status-pills">
                        <span class="status-pill">Periodo seleccionado: {period}</span>
                        <span class="status-pill">Moneda: {currency}</span>
                    </div>
                </div>
                """.format(period=period_label, currency=currency_label),
                unsafe_allow_html=True,
            )
        with col_right:
            st.markdown(
                f"<div class='refresh-box'><div class='refresh-label'>Última actualización: {last_update_display}</div></div>",
                unsafe_allow_html=True,
            )
            if st.button("Actualizar ahora", key="refresh_now_header"):
                refreshed_at = datetime.now()
                st.session_state["last_refresh_ts"] = refreshed_at
                st.toast("Datos actualizados (demo).")


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
        return df.groupby(pd.Grouper(key=date_col, freq="ME"))[value_col].sum().reset_index()
    if granularity == "Anual":
        return df.groupby(pd.Grouper(key=date_col, freq="Y"))[value_col].sum().reset_index()
    return df.groupby(pd.Grouper(key=date_col, freq="Y"))[value_col].sum().reset_index()


def table_height(rows: int) -> int:
    row_height = int(st.session_state.get("row_height", 34))
    return min(600, max(220, (rows + 1) * row_height))
