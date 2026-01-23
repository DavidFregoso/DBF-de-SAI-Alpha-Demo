from __future__ import annotations

from pathlib import Path

import streamlit as st

from sai_alpha.etl import resolve_dbf_dir
from sai_alpha.filters import (
    AdvancedFilterContext,
    FilterState,
    build_advanced_filters,
    build_filter_state,
    build_global_filters,
)
from sai_alpha.sections import clientes, configuracion, pedidos, productos, resumen, vendedores
from sai_alpha.sections import ventas as ventas_section
from sai_alpha.state import init_state_once
from sai_alpha.ui import apply_theme, load_bundle, load_orders, load_sales


def build_sidebar(
    ventas,
    pedidos_df,
    sections: list[str],
) -> tuple[str, FilterState]:
    logo_path = Path("assets/logo.svg")
    if logo_path.exists():
        st.sidebar.image(str(logo_path), width=180)
    st.sidebar.markdown("**Demo Tienda – Dashboard Ejecutivo**")
    st.sidebar.caption("Tablero comercial para dirección")
    st.sidebar.divider()

    st.session_state.setdefault("nav_section", sections[0])
    selected = st.sidebar.selectbox("Sección", sections, key="nav_section")

    with st.sidebar.expander("Filtros globales", expanded=True):
        global_filters = build_global_filters(ventas)

    advanced_context = AdvancedFilterContext(
        brands=selected in {"Resumen Ejecutivo", "Ventas", "Clientes", "Vendedores", "Productos"},
        categories=selected in {"Resumen Ejecutivo", "Ventas", "Productos"},
        vendors=selected
        in {"Resumen Ejecutivo", "Ventas", "Clientes", "Vendedores", "Productos", "Pedidos por Surtir"},
        sale_origins=selected
        in {"Resumen Ejecutivo", "Ventas", "Clientes", "Vendedores", "Productos", "Pedidos por Surtir"},
        client_origins=selected in {"Resumen Ejecutivo", "Clientes", "Productos"},
        recommendation_sources=selected in {"Resumen Ejecutivo", "Clientes", "Productos"},
        invoice_types=selected in {"Resumen Ejecutivo", "Ventas", "Clientes", "Productos"},
        order_types=selected in {"Resumen Ejecutivo", "Ventas", "Clientes", "Productos", "Pedidos por Surtir"},
        order_statuses=selected == "Pedidos por Surtir",
    )
    advanced_filters = build_advanced_filters(ventas, pedidos_df, advanced_context)

    bundle = st.session_state.setdefault("data_bundle", load_bundle())
    filters = build_filter_state(ventas, pedidos_df, bundle, global_filters, advanced_filters)

    st.sidebar.divider()
    last_update = st.session_state.get("data_max_date")
    if last_update:
        st.sidebar.caption(f"Registros filtrados: {len(filters.sales):,}")
        st.sidebar.caption(f"Última actualización: {last_update:%d/%m/%Y}")
    else:
        st.sidebar.caption(f"Registros filtrados: {len(filters.sales):,}")
    return selected, filters


def run_app() -> None:
    st.set_page_config(page_title="Demo Tienda – Dashboard Ejecutivo", page_icon="🛒", layout="wide")

    bundle = st.session_state.setdefault("data_bundle", load_bundle())
    ventas = st.session_state.setdefault("sales_data", load_sales())
    pedidos_df = st.session_state.setdefault("orders_data", load_orders())

    if ventas.empty:
        dbf_dir = resolve_dbf_dir()
        st.error("No hay datos disponibles. Ejecuta generate_dbfs.py para crear data DBF.")
        st.write("Ruta actual:", str(dbf_dir))
        return

    init_state_once(ventas)
    apply_theme()

    sections = [
        "Resumen Ejecutivo",
        "Ventas",
        "Clientes",
        "Vendedores",
        "Productos",
        "Pedidos por Surtir",
        "Configuración",
    ]
    selected, filters = build_sidebar(ventas, pedidos_df, sections)

    if selected == "Resumen Ejecutivo":
        resumen.render(filters, bundle, ventas, pedidos_df)
    elif selected == "Ventas":
        ventas_section.render(filters)
    elif selected == "Clientes":
        clientes.render(filters, ventas)
    elif selected == "Vendedores":
        vendedores.render(filters)
    elif selected == "Productos":
        productos.render(filters, bundle, ventas)
    elif selected == "Pedidos por Surtir":
        pedidos.render(filters, bundle, ventas)
    elif selected == "Configuración":
        configuracion.render(bundle, ventas)


if __name__ == "__main__":
    run_app()
