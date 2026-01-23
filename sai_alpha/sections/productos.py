from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from sai_alpha.formatting import fmt_int, fmt_money, fmt_num, safe_metric
from sai_alpha.filters import FilterState
from sai_alpha.schema import canonicalize_products, require_columns
from sai_alpha.ui import export_buttons, plotly_colors, render_page_header, table_height


def _inventory_summary(filters: FilterState) -> pd.DataFrame:
    inventory = canonicalize_products(filters.products)
    if inventory.empty:
        return inventory

    required = {"PRODUCT_ID", "PRODUCT_NAME", "STOCK_QTY", "COST_MXN"}
    ok, _ = require_columns(inventory, required)
    if not ok:
        return inventory

    sales = filters.sales
    if "PRODUCT_ID" in sales.columns:
        sales_summary = sales.groupby("PRODUCT_ID").agg(units=("QTY", "sum")).reset_index()
        inventory = inventory.merge(sales_summary, on="PRODUCT_ID", how="left")
        inventory["units"] = inventory["units"].fillna(0)
    else:
        inventory["units"] = 0

    inventory["inventory_value"] = inventory["STOCK_QTY"].fillna(0) * inventory["COST_MXN"].fillna(0)
    return inventory


def render(filters: FilterState, bundle, ventas: pd.DataFrame) -> None:
    render_page_header("Productos", subtitle="Rotación, inventario y productos críticos")

    filtered = filters.sales
    if filtered.empty:
        st.warning("No hay registros con los filtros actuales.")
        return

    inventory = _inventory_summary(filters)
    if inventory.empty:
        st.info("No hay inventario disponible para esta sección.")
        return

    rotation = 0.0
    if inventory["STOCK_QTY"].sum() > 0:
        rotation = inventory["units"].sum() / inventory["STOCK_QTY"].sum()
    inventory_value = inventory["inventory_value"].sum()

    st.markdown("### KPIs clave")
    col1, col2, col3 = st.columns(3)
    with col1:
        safe_metric("SKU analizados", fmt_int(inventory["PRODUCT_ID"].nunique()))
    with col2:
        safe_metric("Rotación", fmt_num(rotation))
    with col3:
        safe_metric("Valor inventario", fmt_money(inventory_value, "MXN"))

    st.divider()
    st.markdown("### Pareto Top 10 productos")
    pareto = (
        filtered.groupby("PRODUCT_NAME")[filters.revenue_column]
        .sum()
        .reset_index()
        .sort_values(filters.revenue_column, ascending=False)
        .head(10)
    )
    fig = px.bar(
        pareto,
        x=filters.revenue_column,
        y="PRODUCT_NAME",
        orientation="h",
        color_discrete_sequence=plotly_colors(),
    )
    fig.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.markdown("### Stock y venta mensual")
    inventory_display = inventory.copy()
    inventory_display["stock_fmt"] = inventory_display["STOCK_QTY"].map(fmt_int)
    inventory_display["units_fmt"] = inventory_display["units"].map(fmt_int)
    inventory_display["value_fmt"] = inventory_display["inventory_value"].map(
        lambda value: fmt_money(value, "MXN")
    )
    st.dataframe(
        inventory_display[["PRODUCT_NAME", "stock_fmt", "units_fmt", "value_fmt"]].head(20),
        use_container_width=True,
        height=table_height(20),
        column_config={
            "PRODUCT_NAME": "Producto",
            "stock_fmt": st.column_config.TextColumn("Existencia"),
            "units_fmt": st.column_config.TextColumn("Unidades vendidas"),
            "value_fmt": st.column_config.TextColumn("Valor inventario"),
        },
    )

    st.divider()
    st.markdown("### Productos por agotarse")
    if "MIN_STOCK" not in inventory.columns:
        inventory["MIN_STOCK"] = inventory["STOCK_QTY"].fillna(0) * 0.2
    low_stock = inventory[inventory["STOCK_QTY"] <= inventory["MIN_STOCK"]].copy()
    if low_stock.empty:
        st.info("No hay productos por agotarse con los datos actuales.")
    else:
        low_stock["stock_fmt"] = low_stock["STOCK_QTY"].map(fmt_int)
        st.dataframe(
            low_stock[["PRODUCT_NAME", "stock_fmt"]].head(15),
            use_container_width=True,
            height=table_height(15),
            column_config={
                "PRODUCT_NAME": "Producto",
                "stock_fmt": st.column_config.TextColumn("Existencia"),
            },
        )

    st.divider()
    st.markdown("### Exportar")
    export_buttons(inventory, "productos")
