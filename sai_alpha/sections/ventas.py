from __future__ import annotations

import pandas as pd
import streamlit as st

import plotly.express as px
from sai_alpha.charts import invoice_type_donut, orders_and_revenue_trend, stacked_channel_over_time
from sai_alpha.formatting import fmt_int, fmt_money, safe_metric
from sai_alpha.filters import FilterState
from sai_alpha.theme import get_plotly_template
from sai_alpha.ui import export_buttons, render_page_header, table_height


def render(filters: FilterState, aggregates: dict) -> None:
    render_page_header("Ventas", subtitle="Evolución, canales y marcas con foco comercial")
    theme_cfg = st.session_state.get("theme_cfg", {})
    plotly_template = get_plotly_template(st.session_state.get("theme", "dark"))

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
    st.markdown("### Tendencia de ventas y pedidos")
    order_col = "FACTURA_ID" if "FACTURA_ID" in filtered.columns else "SALE_ID"
    fig_trend = orders_and_revenue_trend(
        filtered,
        "SALE_DATE",
        filters.revenue_column,
        order_col,
        filters.currency_label,
        filters.granularity,
        theme_cfg,
    )
    fig_trend.update_layout(template=plotly_template)
    st.plotly_chart(fig_trend, use_container_width=True)

    st.divider()
    st.markdown("### Ventas por canal a lo largo del tiempo")
    if "ORIGEN_VENTA" in filtered.columns:
        fig_channel = stacked_channel_over_time(
            filtered,
            "SALE_DATE",
            "ORIGEN_VENTA",
            filters.revenue_column,
            filters.currency_label,
            filters.granularity,
            theme_cfg,
        )
        fig_channel.update_layout(template=plotly_template)
        st.plotly_chart(fig_channel, use_container_width=True)
    else:
        st.info("No hay origen de venta disponible para agrupar.")

    st.divider()
    st.markdown("### Top marcas")
    if "BRAND" in filtered.columns:
        brand = aggregates.get("ventas_by_brand", pd.DataFrame())
        fig_brand = px.bar(
            brand.sort_values(filters.revenue_column, ascending=False).head(12),
            x=filters.revenue_column,
            y="BRAND",
            orientation="h",
            labels={"BRAND": "Marca", filters.revenue_column: f"Ventas ({filters.currency_label})"},
        )
        fig_brand.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
        fig_brand.update_traces(hovertemplate="%{y}<br>%{x:,.2f}<extra></extra>")
        fig_brand.update_xaxes(tickformat=",.2f")
        fig_brand.update_layout(template=plotly_template)
        st.plotly_chart(fig_brand, use_container_width=True)
    else:
        st.info("No hay información de marca disponible en este dataset.")

    st.divider()
    st.markdown("### Tipo de factura")
    if "TIPO_FACTURA" in filtered.columns:
        fig_invoice = invoice_type_donut(
            filtered,
            "TIPO_FACTURA",
            filters.revenue_column,
            filters.currency_label,
            theme_cfg,
        )
        fig_invoice.update_layout(template=plotly_template)
        st.plotly_chart(fig_invoice, use_container_width=True)
    else:
        st.info("No hay tipo de factura disponible.")

    st.divider()
    st.markdown("### Ticket promedio vs pedidos por cliente")
    if "CLIENT_NAME" in filtered.columns:
        client_summary = (
            filtered.groupby("CLIENT_NAME")
            .agg(
                revenue=(filters.revenue_column, "sum"),
                orders=(order_col, "nunique"),
            )
            .reset_index()
        )
        client_summary["ticket"] = client_summary["revenue"] / client_summary["orders"].replace(0, pd.NA)
        client_summary = client_summary.sort_values("revenue", ascending=False).head(50)
        fig_scatter = px.scatter(
            client_summary,
            x="orders",
            y="ticket",
            size="revenue",
            hover_name="CLIENT_NAME",
            labels={"orders": "Pedidos", "ticket": f"Ticket promedio ({filters.currency_label})"},
        )
        fig_scatter.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
        fig_scatter.update_traces(hovertemplate="%{hovertext}<br>Pedidos: %{x:,.0f}<br>Ticket: %{y:,.2f}")
        fig_scatter.update_yaxes(tickformat=",.2f")
        fig_scatter.update_layout(template=plotly_template)
        st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.info("No hay clientes disponibles para construir el scatter de tickets.")

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
