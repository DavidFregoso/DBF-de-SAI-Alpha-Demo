from __future__ import annotations

from datetime import timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from sai_alpha.formatting import fmt_currency, fmt_int, fmt_num, fmt_percent
from sai_alpha.filters import FilterState
from sai_alpha.schema import canonicalize_products, coalesce_column
from sai_alpha.ui import (
    export_buttons,
    normalize_currency,
    plotly_colors,
    render_page_header,
    table_height,
)


def render(filters: FilterState, bundle, ventas: pd.DataFrame) -> None:
    render_page_header("Productos")

    filtered = filters.sales
    if filtered.empty:
        st.warning("No hay registros con los filtros actuales.")
        return

    period_days = max(1, (filters.end_date - filters.start_date).days + 1)
    product_sales = (
        filtered.groupby(["PRODUCT_ID", "PRODUCT_NAME", "BRAND", "CATEGORY"])
        .agg(
            units=("QTY", "sum"),
            revenue=(filters.revenue_column, "sum"),
        )
        .reset_index()
    )
    product_sales["avg_daily_units"] = product_sales["units"] / period_days

    try:
        inventory = canonicalize_products(bundle.productos)
    except ValueError as exc:
        st.error(str(exc))
        return
    inventory = inventory.merge(
        product_sales, on=["PRODUCT_ID", "BRAND", "CATEGORY"], how="left", suffixes=("", "_SALES")
    )
    inventory = coalesce_column(inventory, "PRODUCT_NAME", ["PRODUCT_NAME", "PRODUCT_NAME_SALES"])
    inventory["avg_daily_units"] = inventory["avg_daily_units"].fillna(0.0)
    inventory["DAYS_INVENTORY"] = inventory.apply(
        lambda row: row["STOCK_QTY"] / row["avg_daily_units"] if row["avg_daily_units"] > 0 else None,
        axis=1,
    )

    low_threshold = st.slider("Días de inventario bajo", min_value=3, max_value=30, value=10)
    high_threshold = st.slider("Días de inventario alto", min_value=30, max_value=180, value=90)

    low_stock = inventory[inventory["DAYS_INVENTORY"].notna()]
    low_stock = low_stock[low_stock["DAYS_INVENTORY"] <= low_threshold]
    low_stock = low_stock.sort_values("DAYS_INVENTORY").head(20)

    high_stock = inventory[inventory["DAYS_INVENTORY"].notna()]
    high_stock = high_stock[high_stock["DAYS_INVENTORY"] >= high_threshold]
    high_stock = high_stock.sort_values("DAYS_INVENTORY", ascending=False).head(20)

    required_columns = {"PRODUCT_NAME", "BRAND", "CATEGORY", "STOCK_QTY", "DAYS_INVENTORY"}
    missing_columns = sorted(required_columns - set(inventory.columns))
    if missing_columns:
        st.error(
            "Faltan columnas requeridas para el inventario: " + ", ".join(missing_columns)
        )
        return

    st.markdown("### KPIs clave")
    avg_days = inventory["DAYS_INVENTORY"].dropna().mean()
    avg_label = fmt_num(avg_days) if pd.notna(avg_days) else "N/D"

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("SKU analizados", fmt_int(inventory["PRODUCT_ID"].nunique()))
    col2.metric("SKU críticos", fmt_int(low_stock["PRODUCT_ID"].nunique()))
    col3.metric("SKU sobre-stock", fmt_int(high_stock["PRODUCT_ID"].nunique()))
    col4.metric("Días promedio", avg_label)

    st.divider()
    st.markdown("### Productos por agotarse")
    low_display = low_stock.assign(
        STOCK_QTY_FMT=low_stock["STOCK_QTY"].map(fmt_int),
        DAYS_INVENTORY_FMT=low_stock["DAYS_INVENTORY"].map(fmt_num),
    )
    st.dataframe(
        low_display[["PRODUCT_NAME", "BRAND", "CATEGORY", "STOCK_QTY_FMT", "DAYS_INVENTORY_FMT"]],
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

    st.divider()
    st.markdown("### Productos sobre-stock")
    high_display = high_stock.assign(
        STOCK_QTY_FMT=high_stock["STOCK_QTY"].map(fmt_int),
        DAYS_INVENTORY_FMT=high_stock["DAYS_INVENTORY"].map(fmt_num),
    )
    st.dataframe(
        high_display[["PRODUCT_NAME", "BRAND", "CATEGORY", "STOCK_QTY_FMT", "DAYS_INVENTORY_FMT"]],
        use_container_width=True,
        height=table_height(len(high_display)),
        column_config={
            "PRODUCT_NAME": "Producto",
            "BRAND": "Marca",
            "CATEGORY": "Categoría",
            "STOCK_QTY_FMT": st.column_config.TextColumn("Existencia"),
            "DAYS_INVENTORY_FMT": st.column_config.TextColumn("Días inventario"),
        },
    )

    st.divider()
    st.markdown("### Tendencia vs periodo anterior (productos)")
    prev_start = filters.start_date - timedelta(days=period_days)
    prev_end = filters.start_date - timedelta(days=1)
    ventas_norm, _, _, _ = normalize_currency(ventas, filters.currency_mode)
    prev_sales = ventas_norm[
        (ventas_norm["SALE_DATE"] >= pd.Timestamp(prev_start))
        & (ventas_norm["SALE_DATE"] <= pd.Timestamp(prev_end))
    ]
    prev_sales = prev_sales[prev_sales["BRAND"].isin(filters.brands)]
    prev_sales = prev_sales[prev_sales["CATEGORY"].isin(filters.categories)]
    prev_sales = prev_sales[prev_sales["SELLER_NAME"].isin(filters.vendors)]
    prev_sales = prev_sales[prev_sales["ORIGEN_VENTA"].isin(filters.sale_origins)]
    prev_sales = prev_sales[prev_sales["CLIENT_ORIGIN"].isin(filters.client_origins)]
    prev_sales = prev_sales[prev_sales["RECOMM_SOURCE"].isin(filters.recommendation_sources)]
    prev_sales = prev_sales[prev_sales["TIPO_FACTURA"].isin(filters.invoice_types)]
    prev_sales = prev_sales[prev_sales["TIPO_ORDEN"].isin(filters.order_types)]

    current_prod = (
        filtered.groupby(["PRODUCT_ID", "PRODUCT_NAME"])
        .agg(units=("QTY", "sum"), revenue=(filters.revenue_column, "sum"))
        .reset_index()
    )
    prev_prod = (
        prev_sales.groupby(["PRODUCT_ID", "PRODUCT_NAME"])
        .agg(units_prev=("QTY", "sum"), revenue_prev=(filters.revenue_column, "sum"))
        .reset_index()
    )
    trend = current_prod.merge(prev_prod, on=["PRODUCT_ID", "PRODUCT_NAME"], how="left").fillna(0.0)
    trend["delta_units"] = trend["units"] - trend["units_prev"]
    trend["delta_revenue"] = trend["revenue"] - trend["revenue_prev"]
    trend["delta_pct"] = trend.apply(
        lambda row: (row["delta_revenue"] / row["revenue_prev"] * 100)
        if row["revenue_prev"] > 0
        else 0.0,
        axis=1,
    )

    col_up, col_down = st.columns(2)
    with col_up:
        st.markdown("**Top alzas**")
        top_up = trend.sort_values("delta_revenue", ascending=False).head(10).copy()
        top_up["units_fmt"] = top_up["units"].map(fmt_int)
        top_up["delta_units_fmt"] = top_up["delta_units"].map(fmt_int)
        top_up["revenue_fmt"] = top_up["revenue"].map(
            lambda value: fmt_currency(value, filters.currency_label)
        )
        top_up["delta_revenue_fmt"] = top_up["delta_revenue"].map(
            lambda value: fmt_currency(value, filters.currency_label)
        )
        top_up["delta_pct_fmt"] = top_up["delta_pct"].map(fmt_percent)
        st.dataframe(
            top_up[
                [
                    "PRODUCT_NAME",
                    "units_fmt",
                    "delta_units_fmt",
                    "revenue_fmt",
                    "delta_revenue_fmt",
                    "delta_pct_fmt",
                ]
            ],
            use_container_width=True,
            height=table_height(10),
            column_config={
                "PRODUCT_NAME": "Producto",
                "units_fmt": st.column_config.TextColumn("Unidades"),
                "delta_units_fmt": st.column_config.TextColumn("Δ unidades"),
                "revenue_fmt": st.column_config.TextColumn(f"Ventas ({filters.currency_label})"),
                "delta_revenue_fmt": st.column_config.TextColumn("Δ ventas"),
                "delta_pct_fmt": st.column_config.TextColumn("Δ %"),
            },
        )
    with col_down:
        st.markdown("**Top caídas**")
        top_down = trend.sort_values("delta_revenue", ascending=True).head(10).copy()
        top_down["units_fmt"] = top_down["units"].map(fmt_int)
        top_down["delta_units_fmt"] = top_down["delta_units"].map(fmt_int)
        top_down["revenue_fmt"] = top_down["revenue"].map(
            lambda value: fmt_currency(value, filters.currency_label)
        )
        top_down["delta_revenue_fmt"] = top_down["delta_revenue"].map(
            lambda value: fmt_currency(value, filters.currency_label)
        )
        top_down["delta_pct_fmt"] = top_down["delta_pct"].map(fmt_percent)
        st.dataframe(
            top_down[
                [
                    "PRODUCT_NAME",
                    "units_fmt",
                    "delta_units_fmt",
                    "revenue_fmt",
                    "delta_revenue_fmt",
                    "delta_pct_fmt",
                ]
            ],
            use_container_width=True,
            height=table_height(10),
            column_config={
                "PRODUCT_NAME": "Producto",
                "units_fmt": st.column_config.TextColumn("Unidades"),
                "delta_units_fmt": st.column_config.TextColumn("Δ unidades"),
                "revenue_fmt": st.column_config.TextColumn(f"Ventas ({filters.currency_label})"),
                "delta_revenue_fmt": st.column_config.TextColumn("Δ ventas"),
                "delta_pct_fmt": st.column_config.TextColumn("Δ %"),
            },
        )

    st.divider()
    st.markdown("### Marcas dominantes y variación por periodo")
    brand_summary = (
        filtered.groupby("BRAND")
        .agg(units=("QTY", "sum"), revenue=(filters.revenue_column, "sum"))
        .reset_index()
    )
    brand_prev = (
        prev_sales.groupby("BRAND")[filters.revenue_column].sum().reset_index(name="prev_revenue")
    )
    brand_summary = brand_summary.merge(brand_prev, on="BRAND", how="left").fillna(0.0)
    brand_summary["delta_revenue"] = brand_summary["revenue"] - brand_summary["prev_revenue"]

    fig_brand = px.bar(
        brand_summary.sort_values("revenue", ascending=False).head(12),
        x="revenue",
        y="BRAND",
        orientation="h",
        title=f"Ranking marcas ({filters.currency_label})",
        color_discrete_sequence=plotly_colors(),
    )
    fig_brand.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
    st.plotly_chart(fig_brand, use_container_width=True)

    brand_table = brand_summary.sort_values("delta_revenue", ascending=False).head(12).copy()
    brand_table["units_fmt"] = brand_table["units"].map(fmt_int)
    brand_table["revenue_fmt"] = brand_table["revenue"].map(
        lambda value: fmt_currency(value, filters.currency_label)
    )
    brand_table["prev_revenue_fmt"] = brand_table["prev_revenue"].map(
        lambda value: fmt_currency(value, filters.currency_label)
    )
    brand_table["delta_revenue_fmt"] = brand_table["delta_revenue"].map(
        lambda value: fmt_currency(value, filters.currency_label)
    )
    st.dataframe(
        brand_table[["BRAND", "units_fmt", "revenue_fmt", "prev_revenue_fmt", "delta_revenue_fmt"]],
        use_container_width=True,
        height=table_height(12),
        column_config={
            "BRAND": "Marca",
            "units_fmt": st.column_config.TextColumn("Unidades"),
            "revenue_fmt": st.column_config.TextColumn(f"Ventas ({filters.currency_label})"),
            "prev_revenue_fmt": st.column_config.TextColumn("Periodo anterior"),
            "delta_revenue_fmt": st.column_config.TextColumn("Δ ventas"),
        },
    )

    st.divider()
    st.markdown("### Pareto de productos (Top 15)")
    pareto = (
        filtered.groupby(["PRODUCT_ID", "PRODUCT_NAME"])[filters.revenue_column]
        .sum()
        .reset_index()
        .sort_values(filters.revenue_column, ascending=False)
        .head(15)
    )
    pareto["cum_pct"] = pareto[filters.revenue_column].cumsum() / pareto[filters.revenue_column].sum() * 100

    fig_pareto = go.Figure()
    fig_pareto.add_bar(
        x=pareto["PRODUCT_NAME"],
        y=pareto[filters.revenue_column],
        name=f"Ventas ({filters.currency_label})",
        marker_color=plotly_colors()[0],
    )
    fig_pareto.add_scatter(
        x=pareto["PRODUCT_NAME"],
        y=pareto["cum_pct"],
        name="% acumulado",
        yaxis="y2",
        mode="lines+markers",
        marker_color=plotly_colors()[1],
    )
    fig_pareto.update_layout(
        height=360,
        margin=dict(l=20, r=20, t=40, b=20),
        yaxis=dict(title=f"Ventas ({filters.currency_label})"),
        yaxis2=dict(
            title="% acumulado",
            overlaying="y",
            side="right",
            range=[0, 110],
        ),
    )
    st.plotly_chart(fig_pareto, use_container_width=True)

    st.divider()
    st.markdown("### Exportar")
    export_buttons(trend, "productos_tendencias")
