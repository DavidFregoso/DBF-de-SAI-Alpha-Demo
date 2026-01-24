from app import run_app

import streamlit as st

from sai_alpha.theme import init_theme_state, set_theme
from sai_alpha.ui import init_session_state, render_page_nav, reset_theme_defaults


st.set_page_config(page_title="Configuración", page_icon="⚙️", layout="wide")
init_session_state()
init_theme_state()
render_page_nav("Configuración")


st.markdown("<div class='app-header'>Demo Surtidora de Abarrotes</div>", unsafe_allow_html=True)
st.caption("Dashboard Ejecutivo")

st.title("Configuración")

st.markdown("### Apariencia")
st.radio(
    "Tema",
    ["light", "dark"],
    format_func=lambda value: "Claro" if value == "light" else "Oscuro",
    key="theme",
    horizontal=True,
    on_change=lambda: set_theme(st.session_state.get("theme", "dark")),
)
col1, col2 = st.columns(2)
with col1:
    st.color_picker("Color primario", key="theme_primary")
with col2:
    st.color_picker("Color de acento", key="theme_accent")

if st.button("Restaurar defaults", key="reset_theme_defaults_page"):
    reset_theme_defaults()
    set_theme(st.session_state.get("theme", "dark"))

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
run_app()
