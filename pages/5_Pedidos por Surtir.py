from app import run_app

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from sai_alpha.ui import (
    apply_theme,
    export_buttons,
    format_currency_column,
    format_integer_column,
    load_orders,
    load_sales,
    plotly_colors,
    render_page_nav,
    render_sidebar_filters,
    table_height,
)


st.set_page_config(page_title="Pedidos por Surtir", page_icon="🧾", layout="wide")
apply_theme()
render_page_nav("Pedidos por Surtir")

ventas = load_sales()
pedidos = load_orders()

if ventas.empty:
    st.error("No hay datos disponibles. Ejecuta generate_dbfs.py para crear data DBF.")
    st.stop()

filters = render_sidebar_filters(ventas, pedidos)

st.markdown("<div class='app-header'>Demo Surtidora de Abarrotes</div>", unsafe_allow_html=True)
st.caption("Dashboard Ejecutivo")

st.title("Pedidos por Surtir")

if filters.pedidos is None or filters.pedidos.empty:
    st.warning("No hay pedidos en el rango seleccionado.")
    st.stop()

pending = filters.pedidos.copy()
pending = pending[pending["STATUS"].isin(["Pendiente", "Parcial"])].copy()
pending["PENDING_VALUE"] = pending["QTY_PENDING"] * pending["PRICE_MXN"].fillna(0)
pending["AGE_DAYS"] = (filters.end_date - pending["ORDER_DATE"].dt.date).apply(lambda x: x.days)

pending_count = pending["ORDER_ID"].nunique()
pending_value = pending["PENDING_VALUE"].sum()
avg_age = pending["AGE_DAYS"].mean() if not pending.empty else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Pedidos pendientes", f"{pending_count:,}")
col2.metric("Unidades pendientes", f"{pending['QTY_PENDING'].sum():,}")
col3.metric("Valor pendiente", f"$ {pending_value:,.2f}")
col4.metric("Edad promedio", f"{avg_age:.2f} días")

st.markdown("### Aging de pedidos")
aging_bins = pd.cut(
    pending["AGE_DAYS"],
    bins=[-1, 7, 14, 30, np.inf],
    labels=["0-7 días", "8-14 días", "15-30 días", "30+ días"],
)
aging_summary = pending.groupby(aging_bins).agg(
    pedidos=("ORDER_ID", "nunique"),
    valor=("PENDING_VALUE", "sum"),
).reset_index(names="Aging")
fig_aging = px.bar(
    aging_summary,
    x="Aging",
    y="valor",
    title="Valor pendiente por antigüedad",
    color_discrete_sequence=plotly_colors(),
)
fig_aging.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
st.plotly_chart(fig_aging, use_container_width=True)

st.markdown("### Pendientes por vendedor")
by_vendor = (
    pending.groupby("SELLER_NAME")
    .agg(pedidos=("ORDER_ID", "nunique"), valor=("PENDING_VALUE", "sum"))
    .reset_index()
    .sort_values("valor", ascending=False)
)

st.dataframe(
    by_vendor,
    use_container_width=True,
    height=table_height(len(by_vendor)),
    column_config={
        "SELLER_NAME": "Vendedor",
        "pedidos": format_integer_column("Pedidos"),
        "valor": format_currency_column("Valor pendiente"),
    },
)

st.markdown("### Pendientes por cliente")
by_client = (
    pending.groupby("CLIENT_NAME")
    .agg(pedidos=("ORDER_ID", "nunique"), valor=("PENDING_VALUE", "sum"))
    .reset_index()
    .sort_values("valor", ascending=False)
    .head(20)
)

st.dataframe(
    by_client,
    use_container_width=True,
    height=table_height(len(by_client)),
    column_config={
        "CLIENT_NAME": "Cliente",
        "pedidos": format_integer_column("Pedidos"),
        "valor": format_currency_column("Valor pendiente"),
    },
)

st.markdown("### Exportar")
export_buttons(pending, "pedidos_pendientes")
run_app()
