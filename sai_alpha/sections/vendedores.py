from __future__ import annotations

import plotly.express as px
import streamlit as st

from sai_alpha.formatting import fmt_currency, fmt_int
from sai_alpha.filters import FilterState
from sai_alpha.ui import (
    export_buttons,
    plotly_colors,
    render_page_header,
    table_height,
)


def render(filters: FilterState) -> None:
    render_page_header("Vendedores")

    filtered = filters.sales
    if filtered.empty:
        st.warning("No hay registros con los filtros actuales.")
        return

    seller_summary = (
        filtered.groupby(["SELLER_NAME", "REGION", "TEAM"])
        .agg(
            revenue=(filters.revenue_column, "sum"),
            units=("QTY", "sum"),
            orders=("FACTURA_ID", "nunique"),
            clients=("CLIENT_ID", "nunique"),
        )
        .reset_index()
        .sort_values("revenue", ascending=False)
    )

    revenue_total = seller_summary["revenue"].sum()
    orders_total = seller_summary["orders"].sum()
    top_vendor = seller_summary.iloc[0]["SELLER_NAME"] if not seller_summary.empty else "N/A"

    st.markdown("### KPIs clave")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(f"Ventas ({filters.currency_label})", fmt_currency(revenue_total, filters.currency_label))
    col2.metric("Pedidos", fmt_int(orders_total))
    col3.metric("Vendedores activos", fmt_int(seller_summary["SELLER_NAME"].nunique()))
    col4.metric("Top vendedor", top_vendor)

    st.divider()
    st.markdown("### Desempeño por vendedor")
    fig = px.bar(
        seller_summary.head(12),
        x="revenue",
        y="SELLER_NAME",
        orientation="h",
        title=f"Top vendedores ({filters.currency_label})",
        color_discrete_sequence=plotly_colors(),
    )
    fig.update_layout(height=360, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)

    col_left, col_right = st.columns(2)
    with col_left:
        region = seller_summary.groupby("REGION")["revenue"].sum().reset_index()
        fig_region = px.pie(
            region,
            names="REGION",
            values="revenue",
            title="Ventas por región",
            color_discrete_sequence=plotly_colors(),
        )
        fig_region.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_region, use_container_width=True)
    with col_right:
        channel = filtered.groupby("ORIGEN_VENTA")[filters.revenue_column].sum().reset_index()
        fig_channel = px.bar(
            channel,
            x="ORIGEN_VENTA",
            y=filters.revenue_column,
            title="Ventas por origen de venta",
            color_discrete_sequence=plotly_colors(),
        )
        fig_channel.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_channel, use_container_width=True)

    st.divider()
    st.markdown("### Tabla detallada")
    seller_summary = seller_summary.copy()
    seller_summary["revenue_fmt"] = seller_summary["revenue"].map(
        lambda value: fmt_currency(value, filters.currency_label)
    )
    seller_summary["units_fmt"] = seller_summary["units"].map(fmt_int)
    seller_summary["orders_fmt"] = seller_summary["orders"].map(fmt_int)
    seller_summary["clients_fmt"] = seller_summary["clients"].map(fmt_int)
    st.dataframe(
        seller_summary[
            [
                "SELLER_NAME",
                "REGION",
                "TEAM",
                "revenue_fmt",
                "units_fmt",
                "orders_fmt",
                "clients_fmt",
            ]
        ],
        use_container_width=True,
        height=table_height(len(seller_summary)),
        column_config={
            "SELLER_NAME": "Vendedor",
            "REGION": "Región",
            "TEAM": "Equipo",
            "revenue_fmt": st.column_config.TextColumn(f"Ventas ({filters.currency_label})"),
            "units_fmt": st.column_config.TextColumn("Unidades"),
            "orders_fmt": st.column_config.TextColumn("Pedidos"),
            "clients_fmt": st.column_config.TextColumn("Clientes"),
        },
    )

    st.divider()
    st.markdown("### Exportar")
    export_buttons(seller_summary, "vendedores_kpi")
