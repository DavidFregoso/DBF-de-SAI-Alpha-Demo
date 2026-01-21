from __future__ import annotations

import streamlit as st

from sai_alpha.kpi import kpis_by_dimension
from sai_alpha.ui import export_buttons, load_sales, sidebar_filters


st.set_page_config(page_title="Vendedores", page_icon="🧑‍💼", layout="wide")

ventas = load_sales()

if ventas.empty:
    st.error("No hay datos disponibles. Ejecuta generate_dbfs.py para crear data DBF.")
else:
    filtered = sidebar_filters(ventas)
    st.title("Vendedores")
    st.caption("Rendimiento de fuerza comercial")

    vendedores_kpi = kpis_by_dimension(filtered, "VENDOR_NAME")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Ranking por ventas")
        st.dataframe(vendedores_kpi.head(12), use_container_width=True)
    with col2:
        st.subheader("Ventas por región")
        region = filtered.groupby("REGION")["REVENUE"].sum().reset_index()
        st.bar_chart(region, x="REGION", y="REVENUE", use_container_width=True)

    export_buttons(vendedores_kpi, "vendedores_kpi")
