from __future__ import annotations

import streamlit as st

from sai_alpha.state import LatestPeriods
from sai_alpha.ui import render_page_header


def render() -> None:
    render_page_header("Configuración")

    latest: LatestPeriods = st.session_state["latest_periods"]

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
    st.markdown("### Estado de datos")
    st.write(f"Datos cargados: desde {latest.min_date:%d/%m/%Y} hasta {latest.max_date:%d/%m/%Y}.")
    st.write(
        "Última semana disponible: "
        f"semana {latest.latest_week} del {latest.latest_week_year}."
    )
    st.write(
        "Último mes disponible: "
        f"{latest.latest_month:02d}/{latest.latest_month_year}."
    )
    st.write(f"Último día disponible: {latest.latest_day:%d/%m/%Y}.")

    st.info("Los cambios de tema se aplican automáticamente en la siguiente interacción.")
