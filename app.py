from __future__ import annotations

import streamlit as st

from sai_alpha.etl import resolve_dbf_dir
from sai_alpha.filters import render_sidebar_filters
from sai_alpha.sections import clientes, configuracion, pedidos, productos, resumen, vendedores
from sai_alpha.state import init_state_once
from sai_alpha.ui import REQUIRED_SALES_COLUMNS, apply_theme, load_bundle, load_orders, load_sales


def _assert_required_columns(df, required, label) -> str:
    missing = sorted(required - set(df.columns))
    assert not missing, f"[schema check] Missing columns in {label}: {', '.join(missing)}"
    return f"{label}: OK"


def _validate_product_schema(productos) -> None:
    if "PRODUCT_NAME" in productos.columns:
        return
    dbf_dir = resolve_dbf_dir()
    st.error("Falta la columna PRODUCT_NAME en el inventario (productos).")
    st.write("DBF cargado:", str(dbf_dir / "productos.dbf"))
    st.write("Columnas disponibles:", list(productos.columns))
    st.stop()


def _run_schema_checks() -> None:
    bundle = load_bundle()
    ventas = load_sales()
    _validate_product_schema(bundle.productos)
    results = [
        _assert_required_columns(ventas, REQUIRED_SALES_COLUMNS, "ventas"),
        _assert_required_columns(
            bundle.productos,
            {"PRODUCT_ID", "PRODUCT_NAME", "BRAND", "CATEGORY", "STOCK_QTY"},
            "productos",
        ),
    ]
    if bundle.pedidos is not None and not bundle.pedidos.empty:
        results.append(
            _assert_required_columns(
                bundle.pedidos,
                {"ORDER_ID", "PRODUCT_ID", "PRODUCT_NAME", "ORDER_DATE"},
                "pedidos",
            )
        )
    st.caption("Schema check: " + " | ".join(results))


def run_app() -> None:
    st.set_page_config(page_title="Demo Tienda – Dashboard Ejecutivo", page_icon="🛒", layout="wide")
    _run_schema_checks()

    bundle = st.session_state.setdefault("data_bundle", load_bundle())
    ventas = st.session_state.setdefault("sales_data", load_sales())
    pedidos = st.session_state.setdefault("orders_data", load_orders())

    if ventas.empty:
        st.error("No hay datos disponibles. Ejecuta generate_dbfs.py para crear data DBF.")
        return

    init_state_once(ventas)
    apply_theme()

    st.sidebar.markdown("**Demo Tienda**")
    st.sidebar.caption("Dashboard Ejecutivo")
    st.sidebar.divider()

    sections = [
        "Resumen Ejecutivo",
        "Clientes",
        "Vendedores",
        "Productos",
        "Pedidos por Surtir",
        "Configuración",
    ]
    st.session_state.setdefault("nav_section", sections[0])
    selected = st.sidebar.selectbox("Menú", sections, key="nav_section")

    filters = render_sidebar_filters(ventas, pedidos)

    if selected == "Resumen Ejecutivo":
        resumen.render(filters, bundle, ventas, pedidos)
    elif selected == "Clientes":
        clientes.render(filters)
    elif selected == "Vendedores":
        vendedores.render(filters)
    elif selected == "Productos":
        productos.render(filters, bundle, ventas)
    elif selected == "Pedidos por Surtir":
        pedidos.render(filters)
    elif selected == "Configuración":
        configuracion.render()


if __name__ == "__main__":
    run_app()
