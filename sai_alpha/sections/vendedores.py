from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from sai_alpha.formatting import fmt_int, fmt_money, safe_metric
from sai_alpha.filters import FilterState
from sai_alpha.ui import export_buttons, plotly_colors, render_page_header, table_height


def render(filters: FilterState, aggregates: dict) -> None:
    render_page_header("Vendedores", subtitle="Desempeño individual y comparativo")

    filtered = filters.sales
    if filtered.empty:
        st.warning("No hay registros con los filtros actuales.")
        return

    if "SELLER_NAME" not in filtered.columns:
        st.info("No hay información de vendedores en ventas.dbf.")
        return

    seller_summary = aggregates.get("seller_summary", pd.DataFrame())
    if seller_summary.empty:
        st.info("No hay suficientes ventas para mostrar el desempeño de vendedores.")
        return

    revenue_total = seller_summary["revenue"].sum()
    orders_total = seller_summary["orders"].sum()
    if "SALE_DATE" in filtered.columns:
        avg_daily = revenue_total / max(1, filtered["SALE_DATE"].dt.date.nunique())
    else:
        avg_daily = 0

    st.markdown("### KPIs clave")
    col1, col2, col3 = st.columns(3)
    with col1:
        safe_metric(f"Ventas ({filters.currency_label})", fmt_money(revenue_total, filters.currency_label))
    with col2:
        safe_metric("Venta promedio diaria", fmt_money(avg_daily, filters.currency_label))
    with col3:
        safe_metric("Pedidos", fmt_int(orders_total))

    st.divider()
    st.markdown("### Ranking de vendedores")
    top_table = seller_summary.head(10).copy()
    top_table["revenue_fmt"] = top_table["revenue"].map(
        lambda value: fmt_money(value, filters.currency_label)
    )
    top_table["orders_fmt"] = top_table["orders"].map(fmt_int)
    st.dataframe(
        top_table[["SELLER_NAME", "revenue_fmt", "orders_fmt"]],
        use_container_width=True,
        height=table_height(len(top_table)),
        column_config={
            "SELLER_NAME": "Vendedor",
            "revenue_fmt": st.column_config.TextColumn(f"Ventas ({filters.currency_label})"),
            "orders_fmt": st.column_config.TextColumn("Pedidos"),
        },
    )

    st.divider()
    st.markdown("### Comparativo de ventas")
    fig = px.bar(
        seller_summary.head(12),
        x="revenue",
        y="SELLER_NAME",
        orientation="h",
        color_discrete_sequence=plotly_colors(),
    )
    fig.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.markdown("### Tendencia por vendedor")
    selected_vendor = st.selectbox("Vendedor", seller_summary["SELLER_NAME"].unique().tolist())
    seller_trend = aggregates.get("seller_trend", pd.DataFrame())
    if seller_trend.empty:
        st.info("No hay suficiente información para construir la tendencia.")
        return
    series = seller_trend[seller_trend["SELLER_NAME"] == selected_vendor]
    fig_trend = px.line(
        series,
        x="SALE_DATE",
        y=filters.revenue_column,
        markers=True,
        color_discrete_sequence=plotly_colors(),
    )
    fig_trend.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
    fig_trend.update_traces(hovertemplate="%{x|%d/%m/%Y}<br>Ventas: %{y:,.2f}<extra></extra>")
    st.plotly_chart(fig_trend, use_container_width=True)

    st.divider()
    st.markdown("### Exportar")
    export_buttons(seller_summary, "vendedores")
