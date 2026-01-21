from __future__ import annotations

import streamlit as st

from sai_alpha.kpi import kpis_by_dimension
from sai_alpha.ui import export_buttons, load_sales, sidebar_filters


st.set_page_config(page_title="Productos", page_icon="📦", layout="wide")

ventas = load_sales()

if ventas.empty:
    st.error("No hay datos disponibles. Ejecuta generate_dbfs.py para crear data DBF.")
else:
    filtered = sidebar_filters(ventas)
    st.title("Productos")
    st.caption("Análisis de portafolio y marcas")

    productos_kpi = kpis_by_dimension(filtered, "PRODUCT_NAME")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Top productos por ventas")
        st.dataframe(productos_kpi.head(15), use_container_width=True)
    with col2:
        st.subheader("Ventas por categoría")
        categoria = filtered.groupby("CATEGORY")["REVENUE"].sum().reset_index()
        st.bar_chart(categoria, x="CATEGORY", y="REVENUE", use_container_width=True)

    export_buttons(productos_kpi, "productos_kpi")
