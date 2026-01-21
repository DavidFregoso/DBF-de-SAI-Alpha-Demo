from __future__ import annotations

import streamlit as st

from sai_alpha.kpi import kpis_by_dimension
from sai_alpha.ui import export_buttons, load_sales, sidebar_filters


st.set_page_config(page_title="Clientes", page_icon="🧾", layout="wide")

ventas = load_sales()

if ventas.empty:
    st.error("No hay datos disponibles. Ejecuta generate_dbfs.py para crear data DBF.")
else:
    filtered = sidebar_filters(ventas)
    st.title("Clientes")
    st.caption("Ranking de clientes y desempeño comercial")

    clientes_kpi = kpis_by_dimension(filtered, "CLIENT_NAME")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader("Top clientes por ventas")
        st.dataframe(clientes_kpi.head(15), use_container_width=True)
    with col2:
        st.subheader("Ventas por canal")
        canal = filtered.groupby("CHANNEL")["REVENUE"].sum().reset_index()
        st.bar_chart(canal, x="CHANNEL", y="REVENUE", use_container_width=True)

    export_buttons(clientes_kpi, "clientes_kpi")
