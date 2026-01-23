from __future__ import annotations

import streamlit as st

from sai_alpha.formatting import fmt_int
from sai_alpha.schema import require_columns
from sai_alpha.ui import render_page_header


def _render_dataset_card(title: str, df, required: set[str]) -> None:
    with st.container(border=True):
        st.markdown(f"**{title}**")
        st.write(f"Registros: {fmt_int(len(df))}")
        if df.empty:
            st.caption("No hay datos cargados.")
            return
        ok, missing = require_columns(df, required)
        if ok:
            st.success("Columnas clave: OK")
        else:
            st.warning("Faltan columnas clave: " + ", ".join(missing))
        st.caption("Columnas detectadas: " + ", ".join(sorted(df.columns)))


def render(bundle, ventas) -> None:
    render_page_header("Configuración", subtitle="Tema y diagnóstico de datos")

    st.markdown("### Apariencia")
    col1, col2 = st.columns(2)
    with col1:
        st.color_picker("Color primario", key="theme_primary")
    with col2:
        st.color_picker("Color de acento", key="theme_accent")

    st.selectbox(
        "Densidad de tablas",
        ["Compacta", "Confortable", "Amplia"],
        key="table_density",
    )

    st.divider()
    st.markdown("### Diagnóstico de datos")
    st.caption("Esto significa: validamos que las tablas clave estén disponibles sin detener la demo.")

    _render_dataset_card(
        "Ventas",
        ventas,
        {"SALE_DATE", "PRODUCT_ID", "CLIENT_ID", "REVENUE_MXN"},
    )
    _render_dataset_card(
        "Productos",
        bundle.productos,
        {"PRODUCT_ID", "PRODUCT_NAME", "BRAND", "CATEGORY", "STOCK_QTY"},
    )
    _render_dataset_card(
        "Clientes",
        bundle.clientes,
        {"CLIENT_ID", "CLIENT_NAME"},
    )
    _render_dataset_card(
        "Vendedores",
        bundle.vendedores,
        {"SELLER_ID", "SELLER_NAME"},
    )
    if bundle.pedidos is not None:
        _render_dataset_card(
            "Pedidos",
            bundle.pedidos,
            {"ORDER_ID", "ORDER_DATE", "STATUS"},
        )

    st.info("Los cambios de tema se aplican automáticamente en la siguiente interacción.")
