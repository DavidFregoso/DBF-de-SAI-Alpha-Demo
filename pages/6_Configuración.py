from __future__ import annotations

import streamlit as st

from sai_alpha.ui import apply_theme, init_session_state, render_page_nav


st.set_page_config(page_title="Configuración", page_icon="⚙️", layout="wide")
init_session_state()
apply_theme()
render_page_nav("Configuración")

st.markdown("<div class='app-header'>Demo Tienda – Dashboard Ejecutivo</div>", unsafe_allow_html=True)
st.caption("Abarrotes / Bebidas / Botanas / Lácteos")

st.title("Configuración")

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

st.markdown("### Preferencias de tiempo")
st.slider(
    "Ventana de tiempo por defecto (días)",
    min_value=30,
    max_value=365,
    step=15,
    key="default_window_days",
)

st.info("Los cambios se aplican automáticamente en la siguiente interacción.")
