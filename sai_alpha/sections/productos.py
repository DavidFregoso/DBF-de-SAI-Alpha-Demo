from __future__ import annotations

import pandas as pd
import streamlit as st

import plotly.express as px
import plotly.graph_objects as go

from sai_alpha.etl import normalize_columns, resolve_dbf_dir
from sai_alpha.formatting import fmt_int, fmt_money, fmt_num, fmt_units, safe_metric
from sai_alpha.filters import FilterState
from sai_alpha.schema import ensure_inventory_columns, resolve_column
from sai_alpha.theme import get_plotly_template
from sai_alpha.ui import export_buttons, notify_once, render_page_header, table_height


def render(filters: FilterState, aggregates: dict) -> None:
    render_page_header("Productos", subtitle="Rotación, inventario y productos críticos")
    plotly_template = get_plotly_template(st.session_state.get("theme", "dark"))

    filtered = filters.sales
    if filtered.empty:
        st.warning("No hay registros con los filtros actuales.")
        return

    period_days = max(1, (filters.end_date - filters.start_date).days + 1)
    sales_units = pd.DataFrame()
    qty_col = resolve_column(filtered, ["QTY", "UNITS", "CANTIDAD", "PIEZAS", "UNITS_SOLD", "SOLD_UNITS"])
    if "PRODUCT_ID" in filtered.columns and qty_col:
        sales_units = filtered.groupby("PRODUCT_ID").agg(units=(qty_col, "sum")).reset_index()

    inventory_source = resolve_dbf_dir() / "productos.dbf"
    inventory = normalize_columns(aggregates.get("inventory_summary", pd.DataFrame()), "productos", inventory_source)
    inventory, warnings = ensure_inventory_columns(inventory, period_days=period_days, sales_units=sales_units)
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
        for warning in warnings:
            notify_once("inventory_warning_cost_price", warning, level="warning")

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

        inventory["rotation"] = inventory["units"] / inventory["STOCK_QTY"].replace(0, pd.NA)
        inventory["rotation"] = inventory["rotation"].fillna(0)
        inventory["margin"] = inventory["PRICE_MXN"].fillna(0) - inventory["COST_MXN"].fillna(0)

        st.divider()
        st.markdown("### Top productos por rotación")
        top_rotation = inventory.sort_values("rotation", ascending=False).head(10).copy()
        top_rotation["rotation_fmt"] = top_rotation["rotation"].map(fmt_num)
        top_rotation["units_fmt"] = top_rotation["units"].map(fmt_int)
        top_rotation["stock_fmt"] = top_rotation["STOCK_QTY"].map(fmt_int)
        st.dataframe(
            top_rotation[["PRODUCT_NAME", "rotation_fmt", "units_fmt", "stock_fmt"]],
            use_container_width=True,
            height=table_height(10),
            column_config={
                "PRODUCT_NAME": "Producto",
                "rotation_fmt": st.column_config.TextColumn("Rotación"),
                "units_fmt": st.column_config.TextColumn("Unidades"),
                "stock_fmt": st.column_config.TextColumn("Stock"),
            },
        )

        st.markdown("### Top productos por margen")
        top_margin = inventory.sort_values("margin", ascending=False).head(10).copy()
        top_margin["margin_fmt"] = top_margin["margin"].map(lambda value: fmt_money(value, "MXN"))
        top_margin["price_fmt"] = top_margin["PRICE_MXN"].map(lambda value: fmt_money(value, "MXN"))
        top_margin["cost_fmt"] = top_margin["COST_MXN"].map(lambda value: fmt_money(value, "MXN"))
        st.dataframe(
            top_margin[["PRODUCT_NAME", "margin_fmt", "price_fmt", "cost_fmt"]],
            use_container_width=True,
            height=table_height(10),
            column_config={
                "PRODUCT_NAME": "Producto",
                "margin_fmt": st.column_config.TextColumn("Margen unitario"),
                "price_fmt": st.column_config.TextColumn("Precio"),
                "cost_fmt": st.column_config.TextColumn("Costo"),
            },
        )

    st.divider()
    st.markdown("### Pareto de productos por facturación")
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
            .head(15)
        )
    if not pareto.empty:
        pareto["cum_pct"] = pareto[filters.revenue_column].cumsum() / pareto[filters.revenue_column].sum() * 100
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=pareto[product_col],
                y=pareto[filters.revenue_column],
                name="Ventas",
                hovertemplate="%{x}<br>%{y:,.2f}<extra></extra>",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=pareto[product_col],
                y=pareto["cum_pct"],
                mode="lines+markers",
                name="% acumulado",
                yaxis="y2",
                hovertemplate="%{x}<br>% acumulado: %{y:.1f}%<extra></extra>",
            )
        )
        fig.update_layout(
            height=340,
            margin=dict(l=20, r=20, t=40, b=20),
            yaxis=dict(title=f"Ventas ({filters.currency_label})", tickformat=",.2f"),
            yaxis2=dict(title="% acumulado", overlaying="y", side="right", tickformat=".0f"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        fig.update_layout(template=plotly_template)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.markdown("### Top 10 productos por facturación")
    if not pareto.empty and product_col:
        fig_top_rev = px.bar(
            pareto.head(10),
            x=product_col,
            y=filters.revenue_column,
            labels={product_col: "Producto", filters.revenue_column: f"Ventas ({filters.currency_label})"},
        )
        fig_top_rev.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
        fig_top_rev.update_traces(hovertemplate="%{x}<br>%{y:,.2f}<extra></extra>")
        fig_top_rev.update_yaxes(tickformat=",.2f")
        fig_top_rev.update_layout(template=plotly_template)
        st.plotly_chart(fig_top_rev, use_container_width=True)

    st.divider()
    st.markdown("### Top 10 productos por unidades")
    qty_col = resolve_column(filtered, ["QTY", "UNITS", "CANTIDAD", "PIEZAS", "UNITS_SOLD", "SOLD_UNITS"])
    if qty_col and product_col:
        top_units = (
            filtered.groupby(product_col)[qty_col]
            .sum()
            .reset_index()
            .sort_values(qty_col, ascending=False)
            .head(10)
        )
        fig_units = px.bar(
            top_units,
            x=product_col,
            y=qty_col,
            labels={product_col: "Producto", qty_col: "Unidades"},
        )
        fig_units.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
        fig_units.update_traces(hovertemplate="%{x}<br>Unidades: %{y:,.0f}<extra></extra>")
        fig_units.update_layout(template=plotly_template)
        st.plotly_chart(fig_units, use_container_width=True)
    else:
        st.info("No hay unidades disponibles para el ranking.")

    st.divider()
    st.markdown("### Rotación vs inventario")
    if inventory_available:
        fig_scatter = px.scatter(
            inventory,
            x="STOCK_QTY",
            y="units",
            color="CATEGORY" if "CATEGORY" in inventory.columns else None,
            size="inventory_value",
            hover_name="PRODUCT_NAME",
            labels={"STOCK_QTY": "Stock", "units": "Unidades"},
        )
        fig_scatter.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
        fig_scatter.update_traces(hovertemplate="%{hovertext}<br>Stock: %{x:,.0f}<br>Unidades: %{y:,.0f}")
        fig_scatter.update_layout(template=plotly_template)
        st.plotly_chart(fig_scatter, use_container_width=True)
    else:
        st.info("No hay inventario suficiente para el scatter.")

    st.divider()
    st.markdown("### Inventario por categoría")
    if inventory_available and "CATEGORY" in inventory.columns:
        category_inv = inventory.groupby("CATEGORY")["inventory_value"].sum().reset_index()
        fig_inv = px.bar(
            category_inv,
            x="CATEGORY",
            y="inventory_value",
            labels={"CATEGORY": "Categoría", "inventory_value": "Valor inventario"},
        )
        fig_inv.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
        fig_inv.update_traces(hovertemplate="%{x}<br>%{y:,.2f}<extra></extra>")
        fig_inv.update_yaxes(tickformat=",.2f")
        fig_inv.update_layout(template=plotly_template)
        st.plotly_chart(fig_inv, use_container_width=True)
    else:
        st.info("No hay categoría disponible para inventario.")

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
    st.markdown("### Alertas: por agotarse")
    if inventory_available:
        if "PRODUCT_NAME" not in inventory.columns:
            st.error(
                "Falta la columna PRODUCT_NAME para mostrar productos por agotarse. "
                "Regenera los DBFs si acabas de actualizar el demo."
            )
            st.write("Fuente DBF:", str(inventory_source))
            st.write("Columnas disponibles:", list(inventory.columns))
            return
        low_stock = inventory[inventory["STOCK_QTY"] <= inventory["MIN_STOCK"]].copy()
        if low_stock.empty:
            fallback = inventory.sort_values("DAYS_INVENTORY", ascending=True).head(10).copy()
            fallback["stock_fmt"] = fallback["STOCK_QTY"].map(fmt_int)
            fallback["days_fmt"] = fallback["DAYS_INVENTORY"].map(fmt_units)
            st.info("No hay alertas críticas. Se muestran los 10 productos con menor cobertura.")
            st.dataframe(
                fallback[["PRODUCT_NAME", "stock_fmt", "days_fmt"]],
                use_container_width=True,
                height=table_height(len(fallback)),
                column_config={
                    "PRODUCT_NAME": "Producto",
                    "stock_fmt": st.column_config.TextColumn("Existencia"),
                    "days_fmt": st.column_config.TextColumn("Días inventario"),
                },
            )
        else:
            low_stock["stock_fmt"] = low_stock["STOCK_QTY"].map(fmt_int)
            low_stock["min_fmt"] = low_stock["MIN_STOCK"].map(fmt_int)
            st.dataframe(
                low_stock[["PRODUCT_NAME", "stock_fmt", "min_fmt"]].head(15),
                use_container_width=True,
                height=table_height(15),
                column_config={
                    "PRODUCT_NAME": "Producto",
                    "stock_fmt": st.column_config.TextColumn("Existencia"),
                    "min_fmt": st.column_config.TextColumn("Mínimo"),
                },
            )
    else:
        st.info("No hay inventario suficiente para evaluar productos por agotarse.")

    st.divider()
    st.markdown("### Alertas: sobre-stock")
    if inventory_available:
        over_stock = inventory[inventory["STOCK_QTY"] >= inventory["MAX_STOCK"]].copy()
        if over_stock.empty:
            st.info("No hay productos sobre-stock con los datos actuales.")
        else:
            over_stock["stock_fmt"] = over_stock["STOCK_QTY"].map(fmt_int)
            over_stock["max_fmt"] = over_stock["MAX_STOCK"].map(fmt_int)
            st.dataframe(
                over_stock[["PRODUCT_NAME", "stock_fmt", "max_fmt"]].head(15),
                use_container_width=True,
                height=table_height(15),
                column_config={
                    "PRODUCT_NAME": "Producto",
                    "stock_fmt": st.column_config.TextColumn("Existencia"),
                    "max_fmt": st.column_config.TextColumn("Máximo"),
                },
            )
    else:
        st.info("No hay inventario suficiente para evaluar sobre-stock.")

    st.divider()
    st.markdown("### Exportar")
    export_buttons(inventory if inventory_available else pd.DataFrame(), "productos")
