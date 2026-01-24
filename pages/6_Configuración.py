from app import run_app

import streamlit as st

from sai_alpha.ui import THEME_QUERY_MAP, init_session_state, init_theme_state, render_page_nav, reset_theme_defaults


st.set_page_config(page_title="Configuración", page_icon="⚙️", layout="wide")
init_session_state()
init_theme_state()
render_page_nav("Configuración")

def _sync_theme_query_param() -> None:
    st.query_params["theme"] = THEME_QUERY_MAP.get(st.session_state.get("theme"), "light")
    st.rerun()


st.markdown("<div class='app-header'>Demo Surtidora de Abarrotes</div>", unsafe_allow_html=True)
st.caption("Dashboard Ejecutivo")

st.title("Configuración")

st.markdown("### Apariencia")
st.radio(
    "Tema",
    ["Claro", "Oscuro"],
    key="theme",
    horizontal=True,
    on_change=_sync_theme_query_param,
)
col1, col2 = st.columns(2)
with col1:
    st.color_picker("Color primario", key="theme_primary")
with col2:
    st.color_picker("Color de acento", key="theme_accent")

if st.button("Restaurar defaults", key="reset_theme_defaults_page"):
    reset_theme_defaults()
    _sync_theme_query_param()

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
