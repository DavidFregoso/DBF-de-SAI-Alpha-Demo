from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from sai_alpha.formatting import fmt_currency, fmt_int, fmt_num
from sai_alpha.filters import FilterState
from sai_alpha.ui import (
    export_buttons,
    plotly_colors,
    render_page_header,
    table_height,
)


def render(filters: FilterState) -> None:
    render_page_header("Pedidos por Surtir")

    if filters.pedidos is None or filters.pedidos.empty:
        st.warning("No hay pedidos en el rango seleccionado.")
        return

    pending = filters.pedidos.copy()
    pending = pending[pending["STATUS"].isin(["Pendiente", "Parcial"])].copy()
    pending["PENDING_VALUE"] = pending["QTY_PENDING"] * pending["PRICE_MXN"].fillna(0)
    pending["AGE_DAYS"] = (filters.end_date - pending["ORDER_DATE"].dt.date).apply(lambda x: x.days)

    pending_count = pending["ORDER_ID"].nunique()
    pending_value = pending["PENDING_VALUE"].sum()
    avg_age = pending["AGE_DAYS"].mean() if not pending.empty else 0

    st.markdown("### KPIs clave")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Pedidos pendientes", fmt_int(pending_count))
    col2.metric("Unidades pendientes", fmt_int(pending["QTY_PENDING"].sum()))
    col3.metric("Valor pendiente", fmt_currency(pending_value, "MXN"))
    col4.metric("Edad promedio", f"{fmt_num(avg_age)} días")

    st.divider()
    st.markdown("### Aging de pedidos")
    aging_bins = pd.cut(
        pending["AGE_DAYS"],
        bins=[-1, 7, 14, 30, np.inf],
        labels=["0-7 días", "8-14 días", "15-30 días", "30+ días"],
    )
    aging_summary = pending.groupby(aging_bins).agg(
        pedidos=("ORDER_ID", "nunique"),
        valor=("PENDING_VALUE", "sum"),
    ).reset_index(names="Aging")
    fig_aging = px.bar(
        aging_summary,
        x="Aging",
        y="valor",
        title="Valor pendiente por antigüedad",
        color_discrete_sequence=plotly_colors(),
    )
    fig_aging.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_aging, use_container_width=True)

    st.divider()
    st.markdown("### Pendientes por vendedor")
    by_vendor = (
        pending.groupby("SELLER_NAME")
        .agg(pedidos=("ORDER_ID", "nunique"), valor=("PENDING_VALUE", "sum"))
        .reset_index()
        .sort_values("valor", ascending=False)
    )
    by_vendor["pedidos_fmt"] = by_vendor["pedidos"].map(fmt_int)
    by_vendor["valor_fmt"] = by_vendor["valor"].map(lambda value: fmt_currency(value, "MXN"))

    st.dataframe(
        by_vendor[["SELLER_NAME", "pedidos_fmt", "valor_fmt"]],
        use_container_width=True,
        height=table_height(len(by_vendor)),
        column_config={
            "SELLER_NAME": "Vendedor",
            "pedidos_fmt": st.column_config.TextColumn("Pedidos"),
            "valor_fmt": st.column_config.TextColumn("Valor pendiente"),
        },
    )

    st.divider()
    st.markdown("### Pendientes por cliente")
    by_client = (
        pending.groupby("CLIENT_NAME")
        .agg(pedidos=("ORDER_ID", "nunique"), valor=("PENDING_VALUE", "sum"))
        .reset_index()
        .sort_values("valor", ascending=False)
        .head(20)
    )
    by_client["pedidos_fmt"] = by_client["pedidos"].map(fmt_int)
    by_client["valor_fmt"] = by_client["valor"].map(lambda value: fmt_currency(value, "MXN"))

    st.dataframe(
        by_client[["CLIENT_NAME", "pedidos_fmt", "valor_fmt"]],
        use_container_width=True,
        height=table_height(len(by_client)),
        column_config={
            "CLIENT_NAME": "Cliente",
            "pedidos_fmt": st.column_config.TextColumn("Pedidos"),
            "valor_fmt": st.column_config.TextColumn("Valor pendiente"),
        },
    )

    st.divider()
    st.markdown("### Exportar")
    export_buttons(pending, "pedidos_pendientes")
