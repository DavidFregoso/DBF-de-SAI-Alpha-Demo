from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from sai_alpha.formatting import fmt_int, fmt_money, fmt_num, safe_metric
from sai_alpha.filters import FilterState
from sai_alpha.schema import canonicalize_products, require_columns
from sai_alpha.ui import build_time_series, plotly_colors, render_page_header, table_height


def _inventory_block(filters: FilterState) -> None:
    inventory = canonicalize_products(filters.products)
    if inventory.empty:
        st.info("No hay inventario disponible para analizar.")
        return

    required = {"PRODUCT_ID", "PRODUCT_NAME", "BRAND", "CATEGORY", "STOCK_QTY"}
    ok, missing = require_columns(inventory, required)
    if not ok:
        st.info("Inventario incompleto. Faltan columnas: " + ", ".join(missing))
        return

    sales = filters.sales
    period_days = max(1, (filters.end_date - filters.start_date).days + 1)
    product_sales = (
        sales.groupby(["PRODUCT_ID"])
        .agg(units=("QTY", "sum"))
        .reset_index()
    )
    product_sales["avg_daily_units"] = product_sales["units"] / period_days

    inventory = inventory.merge(product_sales, on="PRODUCT_ID", how="left")
    inventory["avg_daily_units"] = inventory["avg_daily_units"].fillna(0.0)

    if "MIN_STOCK" not in inventory.columns:
        inventory["MIN_STOCK"] = inventory["STOCK_QTY"].fillna(0) * 0.2
    if "MAX_STOCK" not in inventory.columns:
        inventory["MAX_STOCK"] = inventory["STOCK_QTY"].fillna(0) * 1.6

    inventory["DAYS_INVENTORY"] = inventory.apply(
        lambda row: row["STOCK_QTY"] / row["avg_daily_units"] if row["avg_daily_units"] > 0 else None,
        axis=1,
    )

    low_stock = inventory[inventory["STOCK_QTY"] <= inventory["MIN_STOCK"]].copy()
    over_stock = inventory[inventory["STOCK_QTY"] >= inventory["MAX_STOCK"]].copy()

    if low_stock.empty and over_stock.empty:
        st.info("No hay alertas de inventario con los datos actuales.")
        return

    col_low, col_high = st.columns(2)
    with col_low:
        st.markdown("**Inventario crítico**")
        if low_stock.empty:
            st.caption("Sin productos críticos en este periodo.")
        else:
            low_display = low_stock.assign(
                STOCK_QTY_FMT=low_stock["STOCK_QTY"].map(fmt_int),
                DAYS_INVENTORY_FMT=low_stock["DAYS_INVENTORY"].map(fmt_num),
            ).head(10)
            st.dataframe(
                low_display[
                    ["PRODUCT_NAME", "BRAND", "CATEGORY", "STOCK_QTY_FMT", "DAYS_INVENTORY_FMT"]
                ],
                use_container_width=True,
                height=table_height(len(low_display)),
                column_config={
                    "PRODUCT_NAME": "Producto",
                    "BRAND": "Marca",
                    "CATEGORY": "Categoría",
                    "STOCK_QTY_FMT": st.column_config.TextColumn("Existencia"),
                    "DAYS_INVENTORY_FMT": st.column_config.TextColumn("Días inventario"),
                },
            )
    with col_high:
        st.markdown("**Sobre-stock**")
        if over_stock.empty:
            st.caption("Sin sobre-stock con los parámetros actuales.")
        else:
            over_display = over_stock.assign(
                STOCK_QTY_FMT=over_stock["STOCK_QTY"].map(fmt_int),
                DAYS_INVENTORY_FMT=over_stock["DAYS_INVENTORY"].map(fmt_num),
            ).head(10)
            st.dataframe(
                over_display[
                    ["PRODUCT_NAME", "BRAND", "CATEGORY", "STOCK_QTY_FMT", "DAYS_INVENTORY_FMT"]
                ],
                use_container_width=True,
                height=table_height(len(over_display)),
                column_config={
                    "PRODUCT_NAME": "Producto",
                    "BRAND": "Marca",
                    "CATEGORY": "Categoría",
                    "STOCK_QTY_FMT": st.column_config.TextColumn("Existencia"),
                    "DAYS_INVENTORY_FMT": st.column_config.TextColumn("Días inventario"),
                },
            )


def render(filters: FilterState, bundle, ventas: pd.DataFrame, pedidos: pd.DataFrame | None) -> None:
    render_page_header("Resumen Ejecutivo")

    filtered = filters.sales
    if filtered.empty:
        st.warning("No hay registros con los filtros actuales.")
        return

    revenue = filtered[filters.revenue_column].sum() if filters.revenue_column in filtered.columns else 0
    orders = (
        filtered["FACTURA_ID"].nunique()
        if "FACTURA_ID" in filtered.columns
        else filtered.get("SALE_ID", pd.Series(dtype=object)).nunique()
    )
    clients = filtered["CLIENT_ID"].nunique() if "CLIENT_ID" in filtered.columns else 0
    ticket = revenue / orders if orders else 0

    st.markdown("### KPIs clave")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        safe_metric(f"Facturación ({filters.currency_label})", fmt_money(revenue, filters.currency_label))
    with col2:
        safe_metric("Pedidos", fmt_int(orders))
    with col3:
        safe_metric("Clientes únicos", fmt_int(clients))
    with col4:
        safe_metric("Ticket promedio", fmt_money(ticket, filters.currency_label))

    st.divider()
    st.markdown("### Tendencia de facturación")
    series = build_time_series(filtered, "SALE_DATE", filters.revenue_column, filters.granularity)
    fig = px.line(
        series,
        x="SALE_DATE",
        y=filters.revenue_column,
        markers=True,
        labels={"SALE_DATE": "Periodo", filters.revenue_column: f"Ventas ({filters.currency_label})"},
        color_discrete_sequence=plotly_colors(),
    )
    fig.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.markdown("### Top productos y clientes")
    col_products, col_clients = st.columns(2)

    with col_products:
        if "PRODUCT_NAME" not in filtered.columns:
            st.info("No hay detalle de productos para mostrar.")
        else:
            top_products = (
                filtered.groupby("PRODUCT_NAME")
                .agg(units=("QTY", "sum"), revenue=(filters.revenue_column, "sum"))
                .reset_index()
                .sort_values("revenue", ascending=False)
                .head(10)
            )
            top_products["revenue_fmt"] = top_products["revenue"].map(
                lambda value: fmt_money(value, filters.currency_label)
            )
            top_products["units_fmt"] = top_products["units"].map(fmt_int)
            st.dataframe(
                top_products[["PRODUCT_NAME", "revenue_fmt", "units_fmt"]],
                use_container_width=True,
                height=table_height(len(top_products)),
                column_config={
                    "PRODUCT_NAME": "Producto",
                    "revenue_fmt": st.column_config.TextColumn(f"Ventas ({filters.currency_label})"),
                    "units_fmt": st.column_config.TextColumn("Unidades"),
                },
            )

    with col_clients:
        if "CLIENT_NAME" not in filtered.columns:
            st.info("No hay detalle de clientes para mostrar.")
        else:
            top_clients = (
                filtered.groupby("CLIENT_NAME")
                .agg(revenue=(filters.revenue_column, "sum"))
                .reset_index()
                .sort_values("revenue", ascending=False)
                .head(10)
            )
            top_clients["revenue_fmt"] = top_clients["revenue"].map(
                lambda value: fmt_money(value, filters.currency_label)
            )
            st.dataframe(
                top_clients[["CLIENT_NAME", "revenue_fmt"]],
                use_container_width=True,
                height=table_height(len(top_clients)),
                column_config={
                    "CLIENT_NAME": "Cliente",
                    "revenue_fmt": st.column_config.TextColumn(f"Ventas ({filters.currency_label})"),
                },
            )

    st.divider()
    st.markdown("### Inventario crítico y sobre-stock")
    _inventory_block(filters)

    st.divider()
    st.markdown("### Pedidos por surtir")
    if filters.pedidos is None or filters.pedidos.empty:
        st.info("No hay pedidos pendientes en este periodo.")
    else:
        pending = filters.pedidos[filters.pedidos["STATUS"].isin(["Pendiente", "Parcial"])].copy()
        pending_value = (pending["QTY_PENDING"].fillna(0) * pending["PRICE_MXN"].fillna(0)).sum()
        col1, col2 = st.columns(2)
        col1.metric("Pedidos pendientes", fmt_int(pending["ORDER_ID"].nunique()))
        col2.metric("Valor pendiente", fmt_money(pending_value, "MXN"))
