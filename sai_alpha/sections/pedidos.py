from __future__ import annotations

import pandas as pd
import streamlit as st

import plotly.express as px

from sai_alpha.formatting import fmt_int, fmt_money, safe_metric
from sai_alpha.filters import FilterState
from sai_alpha.ui import build_time_series, export_buttons, render_page_header, table_height


def render(filters: FilterState, aggregates: dict) -> None:
    render_page_header("Pedidos por Surtir", subtitle="Backlog y monto pendiente")
    if filters.granularity == "Semanal":
        st.caption("Pedidos por surtir (semana seleccionada)")

    pending = aggregates.get("pedidos_pending", pd.DataFrame())
    if pending.empty:
        st.warning("No hay pedidos en el rango seleccionado.")
        return
    warnings = aggregates.get("pedidos_warnings", [])
    if warnings and not st.session_state.get("pedidos_price_warning_shown"):
        for warning in warnings:
            st.warning(warning)
        st.session_state["pedidos_price_warning_shown"] = True

    pending_count = pending["ORDER_ID"].nunique() if "ORDER_ID" in pending.columns else len(pending)
    pending_value = pending["PENDING_VALUE"].sum()

    st.markdown("### KPIs clave")
    col1, col2 = st.columns(2)
    with col1:
        safe_metric("Pedidos pendientes", fmt_int(pending_count))
    with col2:
        safe_metric("Monto pendiente", fmt_money(pending_value, "MXN"))

    st.divider()
    st.markdown("### Pedidos pendientes")
    display = pending.copy()
    display["pending_fmt"] = display["PENDING_VALUE"].map(lambda value: fmt_money(value, "MXN"))
    display["qty_fmt"] = display["QTY_PENDING"].map(fmt_int)
    columns = [
        col
        for col in ["ORDER_ID", "ORDER_DATE", "CLIENT_NAME", "STATUS", "qty_fmt", "pending_fmt"]
        if col in display.columns
    ]
    st.dataframe(
        display[columns].head(25),
        use_container_width=True,
        height=table_height(min(25, len(display))),
        column_config={
            "ORDER_ID": "Pedido",
            "ORDER_DATE": st.column_config.DatetimeColumn("Fecha", format="DD/MM/YYYY"),
            "CLIENT_NAME": "Cliente",
            "STATUS": "Estatus",
            "qty_fmt": st.column_config.TextColumn("Unidades"),
            "pending_fmt": st.column_config.TextColumn("Monto"),
        },
    )

    st.divider()
    granularity_label = {
        "Diario": "diaria",
        "Semanal": "semanal",
        "Mensual": "mensual",
        "Anual": "anual",
    }.get(filters.granularity, "semanal")
    st.markdown(f"### Tendencia {granularity_label} del backlog")
    series = build_time_series(pending, "ORDER_DATE", "PENDING_VALUE", filters.granularity)
    if series.empty:
        st.info("No hay fechas de pedido para construir la tendencia.")
    else:
        fig = px.line(
            series,
            x="ORDER_DATE",
            y="PENDING_VALUE",
            markers=True,
            labels={"ORDER_DATE": "Periodo", "PENDING_VALUE": "Monto pendiente"},
        )
        fig.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
        fig.update_traces(hovertemplate="%{x|%d/%m/%Y}<br>Monto: %{y:,.2f}<extra></extra>")
        fig.update_yaxes(tickformat=",.2f")
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.markdown("### Pendientes por tipo de orden")
    if "TIPO_ORDEN" in pending.columns:
        by_type = pending.groupby("TIPO_ORDEN")["QTY_PENDING"].sum().reset_index()
        fig_type = px.bar(
            by_type,
            x="TIPO_ORDEN",
            y="QTY_PENDING",
            labels={"TIPO_ORDEN": "Tipo de orden", "QTY_PENDING": "Unidades pendientes"},
        )
        fig_type.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
        fig_type.update_traces(hovertemplate="%{x}<br>Unidades: %{y:,.0f}<extra></extra>")
        st.plotly_chart(fig_type, use_container_width=True)
    else:
        st.info("No hay tipo de orden disponible para graficar.")

    st.divider()
    st.markdown("### Valor pendiente por categoría o marca")
    category_col = "CATEGORY" if "CATEGORY" in pending.columns else "BRAND" if "BRAND" in pending.columns else None
    if category_col:
        by_category = (
            pending.groupby(category_col)["PENDING_VALUE"]
            .sum()
            .reset_index()
            .sort_values("PENDING_VALUE", ascending=False)
            .head(12)
        )
        fig_category = px.bar(
            by_category,
            x=category_col,
            y="PENDING_VALUE",
            labels={category_col: "Categoría/Marca", "PENDING_VALUE": "Monto pendiente"},
        )
        fig_category.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
        fig_category.update_traces(hovertemplate="%{x}<br>Monto: %{y:,.2f}<extra></extra>")
        fig_category.update_yaxes(tickformat=",.2f")
        st.plotly_chart(fig_category, use_container_width=True)
    else:
        st.info("No hay categoría o marca disponible para agrupar.")

    st.divider()
    st.markdown("### Pendientes por estatus")
    if "STATUS" in pending.columns:
        status_summary = pending.groupby("STATUS")["QTY_PENDING"].sum().reset_index()
        fig_status = px.bar(
            status_summary,
            x="STATUS",
            y="QTY_PENDING",
            labels={"STATUS": "Estatus", "QTY_PENDING": "Unidades pendientes"},
        )
        fig_status.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
        fig_status.update_traces(hovertemplate="%{x}<br>Unidades: %{y:,.0f}<extra></extra>")
        st.plotly_chart(fig_status, use_container_width=True)
    else:
        st.info("No hay estatus disponible para agrupar.")

    st.divider()
    st.markdown("### Exportar")
    export_buttons(pending, "pedidos_pendientes")
