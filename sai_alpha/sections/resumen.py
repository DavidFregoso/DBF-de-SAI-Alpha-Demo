from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from sai_alpha.formatting import fmt_int, fmt_money, fmt_num, safe_metric
from sai_alpha.filters import FilterState
from sai_alpha.schema import require_columns, resolve_column
from sai_alpha.ui import plotly_colors, render_page_header, table_height


def _inventory_block(inventory: pd.DataFrame, low_stock: pd.DataFrame, over_stock: pd.DataFrame) -> None:
    if inventory.empty:
        st.info("No hay inventario disponible para analizar.")
        return

    required = {"PRODUCT_ID", "PRODUCT_NAME", "BRAND", "CATEGORY", "STOCK_QTY"}
    ok, missing = require_columns(inventory, required)
    if not ok:
        st.info("Inventario incompleto en productos.dbf. Faltan columnas: " + ", ".join(missing))
        return

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


def render(
    filters: FilterState,
    bundle,
    ventas: pd.DataFrame,
    pedidos: pd.DataFrame | None,
    aggregates: dict,
) -> None:
    render_page_header("Resumen Ejecutivo")

    filtered = filters.sales
    if filtered.empty:
        st.warning("No hay registros con los filtros actuales.")
        return

    kpi_sales = aggregates.get("kpi_sales", {})
    revenue = kpi_sales.get("revenue", 0)
    orders = kpi_sales.get("orders", 0)
    clients = kpi_sales.get("clients", 0)
    ticket = kpi_sales.get("ticket", 0)

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
    series = aggregates.get("ventas_by_period", pd.DataFrame())
    fig = px.line(
        series,
        x="SALE_DATE",
        y=filters.revenue_column,
        markers=True,
        labels={"SALE_DATE": "Periodo", filters.revenue_column: f"Ventas ({filters.currency_label})"},
        color_discrete_sequence=plotly_colors(),
    )
    fig.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
    fig.update_traces(hovertemplate="%{x|%d/%m/%Y}<br>Ventas: %{y:,.2f}<extra></extra>")
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.markdown("### Top productos y clientes")
    col_products, col_clients = st.columns(2)

    with col_products:
        product_col = resolve_column(filtered, ["PRODUCT_NAME", "PRODUCT_NAME_X", "PRODUCT_NAME_Y"])
        if not product_col:
            st.info("No hay detalle de productos en ventas.dbf para mostrar.")
        else:
            top_products = aggregates.get("top_products", pd.DataFrame())
            top_products["revenue_fmt"] = top_products["revenue"].map(
                lambda value: fmt_money(value, filters.currency_label)
            )
            top_products["units_fmt"] = top_products["units"].map(fmt_int)
            st.dataframe(
                top_products[[product_col, "revenue_fmt", "units_fmt"]],
                use_container_width=True,
                height=table_height(len(top_products)),
                column_config={
                    product_col: "Producto",
                    "revenue_fmt": st.column_config.TextColumn(f"Ventas ({filters.currency_label})"),
                    "units_fmt": st.column_config.TextColumn("Unidades"),
                },
            )

    with col_clients:
        if "CLIENT_NAME" not in filtered.columns:
            st.info("No hay detalle de clientes en ventas.dbf para mostrar.")
        else:
            top_clients = aggregates.get("top_clients", pd.DataFrame())
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
    _inventory_block(
        aggregates.get("inventory_summary", pd.DataFrame()),
        aggregates.get("inventory_low", pd.DataFrame()),
        aggregates.get("inventory_over", pd.DataFrame()),
    )

    st.divider()
    st.markdown("### Pedidos por surtir")
    pending = aggregates.get("pedidos_pending", pd.DataFrame())
    if pending.empty:
        st.info("No hay pedidos pendientes en este periodo.")
    else:
        pending_value = pending["PENDING_VALUE"].sum()
        col1, col2 = st.columns(2)
        col1.metric("Pedidos pendientes", fmt_int(pending["ORDER_ID"].nunique()))
        col2.metric("Valor pendiente", fmt_money(pending_value, "MXN"))
