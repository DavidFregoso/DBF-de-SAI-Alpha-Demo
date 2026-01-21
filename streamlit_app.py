from __future__ import annotations

import streamlit as st

from sai_alpha.kpi import resumen_kpis
from sai_alpha.ui import export_buttons, load_sales, sidebar_filters


st.set_page_config(page_title="SAI Alpha Dashboard", page_icon="📊", layout="wide")

ventas = load_sales()

if ventas.empty:
    st.error("No hay datos disponibles. Ejecuta generate_dbfs.py para crear data DBF.")
else:
    filtered = sidebar_filters(ventas)
    kpis = resumen_kpis(filtered)

    st.title("Dashboard Ejecutivo y Operativo - SAI Alpha")
    st.caption("MVP DEMO con datos DBF mock (xBase)")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Ventas Totales", f"$ {kpis['total_revenue']:,.2f}")
    col2.metric("Unidades", f"{kpis['total_units']:,}")
    col3.metric("Ticket Promedio", f"$ {kpis['avg_ticket']:,.2f}")
    col4.metric("Marca Líder", kpis["top_brand"])

    st.subheader("Vista rápida")
    st.dataframe(filtered.head(50), use_container_width=True)

    export_buttons(filtered, "ventas_filtradas")
