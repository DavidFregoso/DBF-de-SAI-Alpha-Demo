from __future__ import annotations

import streamlit as st

from sai_alpha.etl import resolve_dbf_dir
from sai_alpha.filters import (
    AdvancedFilterContext,
    FilterState,
    build_advanced_filters,
    build_filter_state,
    build_global_filters,
)
from sai_alpha.aggregates import build_aggregates
from sai_alpha.sections import clientes, configuracion, pedidos, productos, resumen, vendedores
from sai_alpha.sections import ventas as ventas_section
from sai_alpha.state import init_state_once
from sai_alpha.ui import apply_theme, load_bundle, load_orders, load_sales, render_app_header, render_sidebar_header


def build_sidebar(
    ventas,
    pedidos_df,
    sections: list[str],
) -> tuple[str, FilterState]:
    render_sidebar_header()
    st.session_state.setdefault("nav_section", sections[0])
    selected = st.sidebar.radio(
        "Navegación",
        sections,
        key="nav_section",
        label_visibility="visible",
    )

    st.sidebar.divider()
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
    show_section_filters = any(
        [
            advanced_context.brands,
            advanced_context.categories,
            advanced_context.vendors,
            advanced_context.sale_origins,
            advanced_context.client_origins,
            advanced_context.recommendation_sources,
            advanced_context.invoice_types,
            advanced_context.order_types,
            advanced_context.order_statuses,
        ]
    )
    expander = st.sidebar.expander("Filtros de esta sección", expanded=False) if show_section_filters else None
    advanced_filters = build_advanced_filters(ventas, pedidos_df, advanced_context, expander)

    bundle = st.session_state.setdefault("data_bundle", load_bundle())
    filters = build_filter_state(ventas, pedidos_df, bundle, global_filters, advanced_filters)

    st.sidebar.divider()
    last_update = st.session_state.get("data_max_date")
    if last_update:
        st.sidebar.caption(f"Registros filtrados: {len(filters.sales):,}")
        st.sidebar.caption(f"Últimos datos: {last_update:%d/%m/%Y}")
    else:
        st.sidebar.caption(f"Registros filtrados: {len(filters.sales):,}")
    return selected, filters


def run_app() -> None:
    st.set_page_config(
        page_title="Demo Surtidora de Abarrotes – Dashboard Ejecutivo",
        page_icon="🛒",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    bundle = st.session_state.setdefault("data_bundle", load_bundle())
    ventas = st.session_state.setdefault("sales_data", load_sales())
    pedidos_df = st.session_state.setdefault("orders_data", load_orders())

    if ventas is None or ventas.empty:
        dbf_dir = resolve_dbf_dir()
        st.error("No se cargaron ventas. Revisa DBF_DIR o mock data.")
        st.write("Ruta actual:", str(dbf_dir))
        st.stop()

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
    last_update = st.session_state.get("data_max_date")
    last_update_label = last_update.strftime("%d/%m/%Y") if last_update else None
    render_app_header(filters.period_label, filters.currency_label, last_update_label)

    aggregates = build_aggregates(
        ventas,
        filters.sales,
        filters.pedidos,
        filters.products,
        filters.start_date,
        filters.end_date,
        filters.revenue_column,
        filters.currency_label,
        filters.granularity,
        filters.filter_key,
    )

    if selected == "Resumen Ejecutivo":
        resumen.render(filters, bundle, ventas, pedidos_df, aggregates)
    elif selected == "Ventas":
        ventas_section.render(filters, aggregates)
    elif selected == "Clientes":
        clientes.render(filters, aggregates)
    elif selected == "Vendedores":
        vendedores.render(filters, aggregates)
    elif selected == "Productos":
        if bundle.productos is None or bundle.productos.empty:
            st.warning("Productos no cargados; esta sección se omitirá.")
            return
        productos.render(filters, aggregates)
    elif selected == "Pedidos por Surtir":
        if pedidos_df is None or pedidos_df.empty:
            st.warning("Pedidos no cargados; esta sección se omitirá.")
            return
        pedidos.render(filters, aggregates)
    elif selected == "Configuración":
        configuracion.render(bundle, ventas)


if __name__ == "__main__":
    run_app()

# Checklist:
# - theme.py aplicado: sai_alpha/theme.py + sai_alpha/ui.py (apply_theme).
# - filters refactor: sai_alpha/filters.py (periodo, rango, granularidad, persistencia).
# - charts agregados por página: sai_alpha/sections/*.py.
