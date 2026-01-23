from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from sai_alpha.formatting import fmt_int, fmt_money, safe_metric
from sai_alpha.filters import FilterState
from sai_alpha.ui import export_buttons, plotly_colors, render_page_header, table_height


def render(filters: FilterState, ventas: pd.DataFrame) -> None:
    render_page_header("Clientes", subtitle="Clientes activos, origen y recurrencia")

    filtered = filters.sales
    if filtered.empty:
        st.warning("No hay registros con los filtros actuales.")
        return

    revenue = filtered[filters.revenue_column].sum() if filters.revenue_column in filtered.columns else 0
    clients = filtered["CLIENT_ID"].nunique() if "CLIENT_ID" in filtered.columns else 0
    mxn_count = (filtered["CURRENCY"] == "MXN").sum() if "CURRENCY" in filtered.columns else 0
    usd_count = (filtered["CURRENCY"] == "USD").sum() if "CURRENCY" in filtered.columns else 0

    new_clients = 0
    recurrent_clients = 0
    if "CLIENT_ID" in ventas.columns and "SALE_DATE" in ventas.columns:
        first_purchase = ventas.groupby("CLIENT_ID")["SALE_DATE"].min().reset_index(name="first_purchase")
        active_clients = filtered[["CLIENT_ID"]].drop_duplicates()
        active_clients = active_clients.merge(first_purchase, on="CLIENT_ID", how="left")
        new_clients = (active_clients["first_purchase"] >= pd.Timestamp(filters.start_date)).sum()
        recurrent_clients = max(0, len(active_clients) - new_clients)

    st.markdown("### KPIs clave")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        safe_metric(f"Facturación ({filters.currency_label})", fmt_money(revenue, filters.currency_label))
    with col2:
        safe_metric("Clientes activos", fmt_int(clients))
    with col3:
        safe_metric("Nuevos vs recurrentes", f"{fmt_int(new_clients)} / {fmt_int(recurrent_clients)}")
    with col4:
        safe_metric("MXN vs USD", f"{fmt_int(mxn_count)} / {fmt_int(usd_count)}")

    st.divider()
    st.markdown("### Ranking de clientes")
    if "CLIENT_NAME" not in filtered.columns:
        st.info("No hay nombre de cliente disponible para este dataset.")
        return

    invoice_col = "FACTURA_ID" if "FACTURA_ID" in filtered.columns else "SALE_ID"
    client_table = (
        filtered.groupby(["CLIENT_ID", "CLIENT_NAME"])
        .agg(
            revenue=(filters.revenue_column, "sum"),
            units=("QTY", "sum"),
            invoices=(invoice_col, "nunique"),
            last_order=("SALE_DATE", "max"),
        )
        .reset_index()
        .sort_values("revenue", ascending=False)
    )
    client_table["revenue_fmt"] = client_table["revenue"].map(
        lambda value: fmt_money(value, filters.currency_label)
    )
    client_table["units_fmt"] = client_table["units"].map(fmt_int)
    client_table["invoices_fmt"] = client_table["invoices"].map(fmt_int)

    st.dataframe(
        client_table.head(20)[
            [
                "CLIENT_NAME",
                "revenue_fmt",
                "units_fmt",
                "invoices_fmt",
                "last_order",
            ]
        ],
        use_container_width=True,
        height=table_height(20),
        column_config={
            "CLIENT_NAME": "Cliente",
            "revenue_fmt": st.column_config.TextColumn(f"Ventas ({filters.currency_label})"),
            "units_fmt": st.column_config.TextColumn("Unidades"),
            "invoices_fmt": st.column_config.TextColumn("Facturas"),
            "last_order": st.column_config.DatetimeColumn("Última compra", format="DD/MM/YYYY"),
        },
    )

    st.divider()
    st.markdown("### Origen de clientes")
    if "CLIENT_ORIGIN" not in filtered.columns:
        st.info("No hay origen de cliente disponible en este dataset.")
    else:
        origin = filtered.groupby("CLIENT_ORIGIN")["CLIENT_ID"].nunique().reset_index(name="Clientes")
        fig_origin = px.bar(
            origin,
            x="CLIENT_ORIGIN",
            y="Clientes",
            color_discrete_sequence=plotly_colors(),
        )
        fig_origin.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_origin, use_container_width=True)

    st.divider()
    st.markdown("### Exportar")
    export_buttons(client_table, "clientes_ranking")
