from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from sai_alpha import normalize as normalize_utils
from sai_alpha.etl import normalize_columns, resolve_dbf_dir
from sai_alpha.formatting import fmt_int, fmt_money, fmt_num, safe_metric
from sai_alpha.filters import FilterState
from sai_alpha.schema import resolve_column
from sai_alpha.ui import export_buttons, plotly_colors, render_page_header, table_height


def render(filters: FilterState, aggregates: dict) -> None:
    render_page_header("Productos", subtitle="Rotación, inventario y productos críticos")

    filtered = filters.sales
    if filtered.empty:
        st.warning("No hay registros con los filtros actuales.")
        return

    inventory_source = resolve_dbf_dir() / "productos.dbf"
    inventory = normalize_columns(aggregates.get("inventory_summary", pd.DataFrame()), "productos", inventory_source)
    inventory_available = not inventory.empty
    if not inventory_available:
        missing = aggregates.get("inventory_missing", [])
        if missing:
            st.warning(
                "Inventario incompleto en productos.dbf. Faltan columnas: " + ", ".join(missing)
            )
        else:
            st.info("No hay inventario disponible para esta sección.")

    if inventory_available:
        inventory = normalize_utils.ensure_metric(
            inventory,
            "units",
            ["units", "QTY", "UNITS", "CANTIDAD", "PIEZAS", "UNITS_SOLD", "SOLD_UNITS"],
            default=0,
        )
        if inventory["units"].sum() == 0 and "PRODUCT_ID" in filtered.columns:
            qty_col = resolve_column(
                filtered,
                ["QTY", "UNITS", "CANTIDAD", "PIEZAS", "UNITS_SOLD", "SOLD_UNITS"],
            )
            if qty_col:
                sales_units = filtered.groupby("PRODUCT_ID").agg(units=(qty_col, "sum")).reset_index()
                inventory = inventory.merge(sales_units, on="PRODUCT_ID", how="left", suffixes=("", "_SALES"))
                inventory["units"] = inventory["units"].where(
                    inventory["units"].ne(0),
                    inventory["units_SALES"].fillna(0),
                )
                inventory = inventory.drop(columns=["units_SALES"])

        rotation = 0.0
        stock_total = inventory["STOCK_QTY"].sum()
        if stock_total > 0:
            rotation = inventory["units"].sum() / stock_total
        else:
            st.info("La rotación se muestra en 0 porque no hay stock disponible en el periodo.")
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
    product_col = resolve_column(filtered, ["PRODUCT_NAME", "PRODUCT_NAME_X", "PRODUCT_NAME_Y"], required=True)
    if not product_col:
        st.warning(
            "No se encontró el nombre de producto en ventas.dbf. Se buscaron: "
            "PRODUCT_NAME, PRODUCT_NAME_X, PRODUCT_NAME_Y."
        )
        pareto = pd.DataFrame(columns=[filters.revenue_column, "PRODUCT_NAME"])
    else:
        pareto = (
            filtered.groupby(product_col)[filters.revenue_column]
            .sum()
            .reset_index()
            .sort_values(filters.revenue_column, ascending=False)
            .head(10)
        )
    fig = px.bar(
        pareto,
        x=filters.revenue_column,
        y=product_col or "PRODUCT_NAME",
        orientation="h",
        color_discrete_sequence=plotly_colors(),
    )
    fig.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
    fig.update_traces(hovertemplate="%{y}<br>Ventas: %{x:,.2f}<extra></extra>")
    st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.markdown("### Stock y venta mensual")
    if inventory_available:
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
    else:
        st.info("No hay inventario suficiente para mostrar el stock.")

    st.divider()
    st.markdown("### Productos por agotarse")
    if inventory_available:
        if "PRODUCT_NAME" not in inventory.columns:
            st.error(
                "Falta la columna PRODUCT_NAME para mostrar productos por agotarse. "
                "Regenera los DBFs si acabas de actualizar el demo."
            )
            st.write("Fuente DBF:", str(inventory_source))
            st.write("Columnas disponibles:", list(inventory.columns))
            return
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
    else:
        st.info("No hay inventario suficiente para evaluar productos por agotarse.")

    st.divider()
    st.markdown("### Exportar")
    export_buttons(inventory if inventory_available else pd.DataFrame(), "productos")
