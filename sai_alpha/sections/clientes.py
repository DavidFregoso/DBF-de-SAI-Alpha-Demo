from __future__ import annotations

import pandas as pd
import streamlit as st

import plotly.express as px

from sai_alpha.formatting import fmt_int, fmt_money, safe_metric
from sai_alpha.filters import FilterState
from sai_alpha.theme import get_plotly_template
from sai_alpha.ui import export_buttons, render_page_header, table_height


def render(filters: FilterState, aggregates: dict) -> None:
    render_page_header("Clientes", subtitle="Clientes activos, origen y recurrencia")
    plotly_template = get_plotly_template(st.session_state.get("theme", "dark"))

    filtered = filters.sales
    if filtered.empty:
        st.warning("No hay registros con los filtros actuales.")
        return

    kpi_sales = aggregates.get("kpi_sales", {})
    revenue = kpi_sales.get("revenue", 0)
    clients = kpi_sales.get("clients", 0)
    kpi_clients = aggregates.get("clientes_kpi", {})
    new_clients = kpi_clients.get("new_clients", 0)
    recurrent_clients = kpi_clients.get("recurrent_clients", 0)
    mxn_count = kpi_clients.get("mxn_count", 0)
    usd_count = kpi_clients.get("usd_count", 0)

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
        st.info("No hay nombre de cliente disponible en ventas.dbf.")
        return

    client_table = aggregates.get("clientes_summary", pd.DataFrame())
    if client_table.empty:
        st.info("No hay clientes suficientes para construir el ranking.")
    else:
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
    st.markdown("### Top 15 clientes por facturación")
    if not client_table.empty:
        fig_top_clients = px.bar(
            client_table.head(15),
            x="CLIENT_NAME",
            y="revenue",
            labels={"CLIENT_NAME": "Cliente", "revenue": f"Ventas ({filters.currency_label})"},
        )
        fig_top_clients.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
        fig_top_clients.update_traces(hovertemplate="%{x}<br>%{y:,.2f}<extra></extra>")
        fig_top_clients.update_yaxes(tickformat=",.2f")
        fig_top_clients.update_layout(template=plotly_template)
        st.plotly_chart(fig_top_clients, use_container_width=True)

    st.divider()
    st.markdown("### Clientes únicos por periodo")
    if "SALE_DATE" in filtered.columns and "CLIENT_ID" in filtered.columns:
        granularity = filters.granularity
        freq = {"Diario": "D", "Semanal": "W-MON", "Mensual": "ME", "Anual": "Y"}.get(granularity, "W-MON")
        unique_clients = (
            filtered.groupby(pd.Grouper(key="SALE_DATE", freq=freq))["CLIENT_ID"]
            .nunique()
            .reset_index(name="Clientes")
        )
        fig_clients = px.line(
            unique_clients,
            x="SALE_DATE",
            y="Clientes",
            markers=True,
            labels={"SALE_DATE": "Periodo", "Clientes": "Clientes únicos"},
        )
        fig_clients.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
        fig_clients.update_traces(hovertemplate="%{x|%d/%m/%Y}<br>Clientes: %{y:,.0f}<extra></extra>")
        fig_clients.update_layout(template=plotly_template)
        st.plotly_chart(fig_clients, use_container_width=True)
    else:
        st.info("No hay fechas o clientes para construir la tendencia.")

    st.divider()
    st.markdown("### Recomendación / encuesta")
    if "RECOMM_SOURCE" in filtered.columns:
        recommend = (
            filtered.groupby("RECOMM_SOURCE")["CLIENT_ID"].nunique().reset_index(name="Clientes")
        )
        fig_recommend = px.pie(recommend, values="Clientes", names="RECOMM_SOURCE", hole=0.5)
        fig_recommend.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
        fig_recommend.update_traces(hovertemplate="%{label}<br>Clientes: %{value:,.0f}<extra></extra>")
        fig_recommend.update_layout(template=plotly_template)
        st.plotly_chart(fig_recommend, use_container_width=True)
    else:
        st.info("No hay datos de recomendación disponibles.")

    st.divider()
    st.markdown("### Origen de clientes")
    origin = aggregates.get("clientes_origin", pd.DataFrame())
    if origin.empty:
        st.info("No hay origen de cliente disponible en ventas.dbf.")
    else:
        fig_origin = px.bar(
            origin,
            x="CLIENT_ORIGIN",
            y="Clientes",
            labels={"CLIENT_ORIGIN": "Origen", "Clientes": "Clientes"},
        )
        fig_origin.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
        fig_origin.update_traces(hovertemplate="%{x}<br>Clientes: %{y:,.0f}<extra></extra>")
        fig_origin.update_layout(template=plotly_template)
        st.plotly_chart(fig_origin, use_container_width=True)

    st.divider()
    st.markdown("### Exportar")
    export_buttons(client_table, "clientes_ranking")
