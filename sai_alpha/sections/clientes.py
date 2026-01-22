from __future__ import annotations

import plotly.express as px
import streamlit as st

from sai_alpha.filters import FilterState
from sai_alpha.ui import (
    export_buttons,
    format_currency_column,
    format_int,
    format_integer_column,
    format_money,
    plotly_colors,
    render_page_header,
    table_height,
)


def render(filters: FilterState) -> None:
    render_page_header("Clientes")

    filtered = filters.sales
    if filtered.empty:
        st.warning("No hay registros con los filtros actuales.")
        return

    revenue = filtered[filters.revenue_column].sum()
    clients = filtered["CLIENT_ID"].nunique()
    orders = (
        filtered["FACTURA_ID"].nunique()
        if "FACTURA_ID" in filtered.columns
        else filtered["SALE_ID"].nunique()
    )
    mxn_count = (filtered["CURRENCY"] == "MXN").sum() if "CURRENCY" in filtered.columns else 0
    usd_count = (filtered["CURRENCY"] == "USD").sum() if "CURRENCY" in filtered.columns else 0

    st.markdown("### KPIs clave")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric(f"Facturación ({filters.currency_label})", f"$ {format_money(revenue)}")
    col2.metric("Clientes activos", format_int(clients))
    col3.metric("# Facturas", format_int(orders))
    col4.metric("MXN vs USD", f"{format_int(mxn_count)} / {format_int(usd_count)}")

    st.divider()
    st.markdown("### Ranking de clientes")
    client_table = (
        filtered.groupby(["CLIENT_ID", "CLIENT_NAME", "CLIENT_ORIGIN", "RECOMM_SOURCE", "REGION"])
        .agg(
            revenue=(filters.revenue_column, "sum"),
            units=("QTY", "sum"),
            invoices=("FACTURA_ID", "nunique"),
            last_order=("SALE_DATE", "max"),
        )
        .reset_index()
    )
    client_table = client_table.sort_values("revenue", ascending=False)

    max_rows = st.slider("Mostrar Top N", min_value=10, max_value=50, value=20)

    st.dataframe(
        client_table.head(max_rows),
        use_container_width=True,
        height=table_height(max_rows),
        column_config={
            "CLIENT_NAME": "Cliente",
            "CLIENT_ORIGIN": "Origen",
            "RECOMM_SOURCE": "Recomendación/Encuesta",
            "REGION": "Región",
            "revenue": format_currency_column(f"Ventas ({filters.currency_label})"),
            "units": format_integer_column("Unidades"),
            "invoices": format_integer_column("Facturas"),
            "last_order": st.column_config.DatetimeColumn("Última compra", format="DD/MM/YYYY"),
        },
    )

    st.divider()
    st.markdown("### Origen de clientes y actividad")
    col_left, col_right = st.columns(2)
    with col_left:
        origin = filtered.groupby("CLIENT_ORIGIN")["CLIENT_ID"].nunique().reset_index(name="Clientes")
        fig_origin = px.bar(
            origin,
            x="CLIENT_ORIGIN",
            y="Clientes",
            title="Distribución por origen",
            color_discrete_sequence=plotly_colors(),
        )
        fig_origin.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_origin, use_container_width=True)
    with col_right:
        recent = client_table.sort_values("last_order", ascending=False).head(10)
        st.markdown("**Últimas compras**")
        st.dataframe(
            recent[["CLIENT_NAME", "last_order", "revenue"]],
            use_container_width=True,
            height=table_height(len(recent)),
            column_config={
                "CLIENT_NAME": "Cliente",
                "last_order": st.column_config.DatetimeColumn("Última compra", format="DD/MM/YYYY"),
                "revenue": format_currency_column(f"Ventas ({filters.currency_label})"),
            },
        )

    st.divider()
    st.markdown("### Exportar")
    export_buttons(client_table, "clientes_ranking")
