from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from sai_alpha.formatting import fmt_int, fmt_money, safe_metric
from sai_alpha.filters import FilterState
from sai_alpha.ui import export_buttons, plotly_colors, render_page_header, table_height


def render(filters: FilterState, aggregates: dict) -> None:
    render_page_header("Ventas", subtitle="Evolución, canales y marcas con foco comercial")

    filtered = filters.sales
    if filtered.empty:
        st.warning("No hay registros con los filtros actuales.")
        return

    st.markdown("### KPIs clave")
    kpi_sales = aggregates.get("kpi_sales", {})
    revenue = kpi_sales.get("revenue", 0)
    orders = kpi_sales.get("orders", 0)
    clients = kpi_sales.get("clients", 0)
    ticket = kpi_sales.get("ticket", 0)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        safe_metric(f"Facturación ({filters.currency_label})", fmt_money(revenue, filters.currency_label))
    with col2:
        safe_metric("Pedidos", fmt_int(orders))
    with col3:
        safe_metric("Clientes activos", fmt_int(clients))
    with col4:
        safe_metric("Ticket promedio", fmt_money(ticket, filters.currency_label))

    st.divider()
    tabs = st.tabs(["Tendencia", "Por canal", "Por marca"])

    with tabs[0]:
        st.caption("Esto significa: cómo evoluciona la facturación en el periodo.")
        series = aggregates.get("ventas_by_period", pd.DataFrame())
        fig = px.line(
            series,
            x="SALE_DATE",
            y=filters.revenue_column,
            markers=True,
            labels={"SALE_DATE": "Periodo", filters.revenue_column: f"Ventas ({filters.currency_label})"},
            color_discrete_sequence=plotly_colors(),
        )
        fig.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
        fig.update_traces(hovertemplate="%{x|%d/%m/%Y}<br>Ventas: %{y:,.2f}<extra></extra>")
        st.plotly_chart(fig, use_container_width=True)

    with tabs[1]:
        st.caption("Esto significa: qué canales están generando más ventas.")
        channel = aggregates.get("ventas_by_channel", pd.DataFrame())
        if channel.empty:
            channel = pd.DataFrame({"ORIGEN_VENTA": ["No disponible"], filters.revenue_column: [0]})
        fig_channel = px.bar(
            channel.sort_values(filters.revenue_column, ascending=False),
            x="ORIGEN_VENTA",
            y=filters.revenue_column,
            color_discrete_sequence=plotly_colors(),
        )
        fig_channel.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
        fig_channel.update_traces(hovertemplate="%{x}<br>Ventas: %{y:,.2f}<extra></extra>")
        st.plotly_chart(fig_channel, use_container_width=True)

    with tabs[2]:
        st.caption("Esto significa: marcas con mayor participación de ventas.")
        if "BRAND" not in filtered.columns:
            st.info("No hay información de marca disponible en este dataset.")
        else:
            brand = aggregates.get("ventas_by_brand", pd.DataFrame())
            fig_brand = px.bar(
                brand.sort_values(filters.revenue_column, ascending=False).head(12),
                x=filters.revenue_column,
                y="BRAND",
                orientation="h",
                color_discrete_sequence=plotly_colors(),
            )
            fig_brand.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
            fig_brand.update_traces(hovertemplate="%{y}<br>Ventas: %{x:,.2f}<extra></extra>")
            st.plotly_chart(fig_brand, use_container_width=True)

    st.divider()
    st.markdown("### Facturas / pedidos")
    table = aggregates.get("invoice_table", pd.DataFrame())
    if not table.empty:
        table["revenue_fmt"] = table["revenue"].map(lambda value: fmt_money(value, filters.currency_label))
        table["units_fmt"] = table["units"].map(fmt_int)
    display_cols = [
        col
        for col in [
            "FACTURA_ID",
            "SALE_ID",
            "SALE_DATE",
            "CLIENT_NAME",
            "SELLER_NAME",
            "CURRENCY",
            "STATUS",
            "revenue_fmt",
            "units_fmt",
        ]
        if col in table.columns
    ]
    if table.empty:
        st.info("No hay facturas para mostrar con los filtros actuales.")
    else:
        st.dataframe(
            table[display_cols].head(25),
            use_container_width=True,
            height=table_height(min(25, len(table))),
            column_config={
                "FACTURA_ID": "Factura",
                "SALE_ID": "Venta",
                "SALE_DATE": st.column_config.DatetimeColumn("Fecha", format="DD/MM/YYYY"),
                "CLIENT_NAME": "Cliente",
                "SELLER_NAME": "Vendedor",
                "CURRENCY": "Moneda",
                "STATUS": "Estatus",
                "revenue_fmt": st.column_config.TextColumn(f"Ventas ({filters.currency_label})"),
                "units_fmt": st.column_config.TextColumn("Unidades"),
            },
        )

    st.divider()
    st.markdown("### Exportar")
    export_buttons(table, "ventas")
