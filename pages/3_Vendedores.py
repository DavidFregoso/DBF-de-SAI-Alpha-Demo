from __future__ import annotations

import plotly.express as px
import streamlit as st

from sai_alpha.ui import (
    apply_theme,
    export_buttons,
    format_currency_column,
    format_integer_column,
    load_orders,
    load_sales,
    render_sidebar_filters,
    table_height,
)


st.set_page_config(page_title="Vendedores", page_icon="🧑‍💼", layout="wide")
apply_theme()

ventas = load_sales()
pedidos = load_orders()

if ventas.empty:
    st.error("No hay datos disponibles. Ejecuta generate_dbfs.py para crear data DBF.")
    st.stop()

filters = render_sidebar_filters(ventas, pedidos)
filtered = filters.sales

st.markdown("<div class='app-header'>Abarrotes Demo</div>", unsafe_allow_html=True)
st.caption("Dashboard Ejecutivo SAI Alpha (Demo)")

st.title("Vendedores")

if filtered.empty:
    st.warning("No hay registros con los filtros actuales.")
    st.stop()

seller_summary = (
    filtered.groupby(["VENDOR_NAME", "REGION", "TEAM"])
    .agg(
        revenue=(filters.revenue_column, "sum"),
        units=("QUANTITY", "sum"),
        orders=("SALE_ID", "nunique"),
        clients=("CLIENT_ID", "nunique"),
    )
    .reset_index()
    .sort_values("revenue", ascending=False)
)

revenue_total = seller_summary["revenue"].sum()
orders_total = seller_summary["orders"].sum()
top_vendor = seller_summary.iloc[0]["VENDOR_NAME"] if not seller_summary.empty else "N/A"

col1, col2, col3, col4 = st.columns(4)
col1.metric(f"Ventas ({filters.currency_label})", f"$ {revenue_total:,.2f}")
col2.metric("Pedidos", f"{orders_total:,}")
col3.metric("Vendedores activos", f"{seller_summary['VENDOR_NAME'].nunique():,}")
col4.metric("Top vendedor", top_vendor)

st.markdown("### Desempeño por vendedor")
fig = px.bar(
    seller_summary.head(12),
    x="revenue",
    y="VENDOR_NAME",
    orientation="h",
    title=f"Top vendedores ({filters.currency_label})",
)
fig.update_layout(height=360, margin=dict(l=20, r=20, t=40, b=20))
st.plotly_chart(fig, use_container_width=True)

col_left, col_right = st.columns(2)
with col_left:
    region = seller_summary.groupby("REGION")["revenue"].sum().reset_index()
    fig_region = px.pie(region, names="REGION", values="revenue", title="Ventas por región")
    fig_region.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_region, use_container_width=True)
with col_right:
    channel = filtered.groupby("ORIGEN_VTA")[filters.revenue_column].sum().reset_index()
    fig_channel = px.bar(
        channel,
        x="ORIGEN_VTA",
        y=filters.revenue_column,
        title="Ventas por origen de venta",
    )
    fig_channel.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_channel, use_container_width=True)

st.markdown("### Tabla detallada")
st.dataframe(
    seller_summary,
    use_container_width=True,
    height=table_height(len(seller_summary)),
    column_config={
        "VENDOR_NAME": "Vendedor",
        "REGION": "Región",
        "TEAM": "Equipo",
        "revenue": format_currency_column(f"Ventas ({filters.currency_label})"),
        "units": format_integer_column("Unidades"),
        "orders": format_integer_column("Pedidos"),
        "clients": format_integer_column("Clientes"),
    },
)

st.markdown("### Exportar")
export_buttons(seller_summary, "vendedores_kpi")
