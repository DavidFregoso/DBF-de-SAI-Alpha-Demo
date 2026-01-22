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
    col1.metric(f"Facturación ({filters.currency_label})", fmt_currency(revenue, filters.currency_label))
    col2.metric("Clientes activos", fmt_int(clients))
    col3.metric("# Facturas", fmt_int(orders))
    col4.metric("MXN vs USD", f"{fmt_int(mxn_count)} / {fmt_int(usd_count)}")

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
    client_table["revenue_fmt"] = client_table["revenue"].map(
        lambda value: fmt_currency(value, filters.currency_label)
    )
    client_table["units_fmt"] = client_table["units"].map(fmt_int)
    client_table["invoices_fmt"] = client_table["invoices"].map(fmt_int)

    max_rows = st.slider("Mostrar Top N", min_value=10, max_value=50, value=20)

    st.dataframe(
        client_table.head(max_rows)[
            [
                "CLIENT_ID",
                "CLIENT_NAME",
                "CLIENT_ORIGIN",
                "RECOMM_SOURCE",
                "REGION",
                "revenue_fmt",
                "units_fmt",
                "invoices_fmt",
                "last_order",
            ]
        ],
        use_container_width=True,
        height=table_height(max_rows),
        column_config={
            "CLIENT_NAME": "Cliente",
            "CLIENT_ORIGIN": "Origen",
            "RECOMM_SOURCE": "Recomendación/Encuesta",
            "REGION": "Región",
            "revenue_fmt": st.column_config.TextColumn(f"Ventas ({filters.currency_label})"),
            "units_fmt": st.column_config.TextColumn("Unidades"),
            "invoices_fmt": st.column_config.TextColumn("Facturas"),
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
        recent["revenue_fmt"] = recent["revenue"].map(
            lambda value: fmt_currency(value, filters.currency_label)
        )
        st.markdown("**Últimas compras**")
        st.dataframe(
            recent[["CLIENT_NAME", "last_order", "revenue_fmt"]],
            use_container_width=True,
            height=table_height(len(recent)),
            column_config={
                "CLIENT_NAME": "Cliente",
                "last_order": st.column_config.DatetimeColumn("Última compra", format="DD/MM/YYYY"),
                "revenue_fmt": st.column_config.TextColumn(f"Ventas ({filters.currency_label})"),
            },
        )

    st.divider()
    st.markdown("### Exportar")
    export_buttons(client_table, "clientes_ranking")
