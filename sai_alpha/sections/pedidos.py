from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from sai_alpha.formatting import fmt_int, fmt_money, safe_metric
from sai_alpha.filters import FilterState
from sai_alpha.ui import build_time_series, export_buttons, plotly_colors, render_page_header, table_height


def render(filters: FilterState, bundle, ventas: pd.DataFrame) -> None:
    render_page_header("Pedidos por Surtir", subtitle="Backlog y monto pendiente")

    if filters.pedidos is None or filters.pedidos.empty:
        st.warning("No hay pedidos en el rango seleccionado.")
        return

    pending = filters.pedidos.copy()
    pending = pending[pending["STATUS"].isin(["Pendiente", "Parcial"])].copy()
    pending["PENDING_VALUE"] = pending["QTY_PENDING"].fillna(0) * pending["PRICE_MXN"].fillna(0)

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
    st.markdown("### Tendencia semanal del backlog")
    if "ORDER_DATE" not in pending.columns:
        st.info("No hay fechas de pedido para construir la tendencia.")
    else:
        weekly = (
            pending.groupby(pd.Grouper(key="ORDER_DATE", freq="W-MON"))["PENDING_VALUE"]
            .sum()
            .reset_index()
        )
        fig = px.line(
            weekly,
            x="ORDER_DATE",
            y="PENDING_VALUE",
            markers=True,
            color_discrete_sequence=plotly_colors(),
        )
        fig.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.markdown("### Exportar")
    export_buttons(pending, "pedidos_pendientes")
