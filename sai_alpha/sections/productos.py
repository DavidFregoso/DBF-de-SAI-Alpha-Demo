from __future__ import annotations

from datetime import timedelta

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from sai_alpha.filters import FilterState
from sai_alpha.ui import (
    export_buttons,
    format_currency_column,
    format_int,
    format_integer_column,
    format_money,
    format_number_column,
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

    inventory = bundle.productos.copy()
    inventory = inventory.merge(product_sales, on=["PRODUCT_ID", "BRAND", "CATEGORY"], how="left")
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

    st.markdown("### KPIs clave")
    avg_days = inventory["DAYS_INVENTORY"].dropna().mean()
    avg_label = format_money(avg_days) if pd.notna(avg_days) else "N/D"

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("SKU analizados", format_int(inventory["PRODUCT_ID"].nunique()))
    col2.metric("SKU críticos", format_int(low_stock["PRODUCT_ID"].nunique()))
    col3.metric("SKU sobre-stock", format_int(high_stock["PRODUCT_ID"].nunique()))
    col4.metric("Días promedio", avg_label)

    st.divider()
    st.markdown("### Productos por agotarse")
    st.dataframe(
        low_stock[["PRODUCT_NAME", "BRAND", "CATEGORY", "STOCK_QTY", "DAYS_INVENTORY"]],
        use_container_width=True,
        height=table_height(len(low_stock)),
        column_config={
            "PRODUCT_NAME": "Producto",
            "BRAND": "Marca",
            "CATEGORY": "Categoría",
            "STOCK_QTY": format_integer_column("Existencia"),
            "DAYS_INVENTORY": format_number_column("Días inventario"),
        },
    )

    st.divider()
    st.markdown("### Productos sobre-stock")
    st.dataframe(
        high_stock[["PRODUCT_NAME", "BRAND", "CATEGORY", "STOCK_QTY", "DAYS_INVENTORY"]],
        use_container_width=True,
        height=table_height(len(high_stock)),
        column_config={
            "PRODUCT_NAME": "Producto",
            "BRAND": "Marca",
            "CATEGORY": "Categoría",
            "STOCK_QTY": format_integer_column("Existencia"),
            "DAYS_INVENTORY": format_number_column("Días inventario"),
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
        st.dataframe(
            trend.sort_values("delta_revenue", ascending=False).head(10),
            use_container_width=True,
            height=table_height(10),
            column_config={
                "PRODUCT_NAME": "Producto",
                "units": format_integer_column("Unidades"),
                "delta_units": format_integer_column("Δ unidades"),
                "revenue": format_currency_column(f"Ventas ({filters.currency_label})"),
                "delta_revenue": format_currency_column("Δ ventas"),
                "delta_pct": st.column_config.NumberColumn("Δ %", format="%,.2f%%"),
            },
        )
    with col_down:
        st.markdown("**Top caídas**")
        st.dataframe(
            trend.sort_values("delta_revenue", ascending=True).head(10),
            use_container_width=True,
            height=table_height(10),
            column_config={
                "PRODUCT_NAME": "Producto",
                "units": format_integer_column("Unidades"),
                "delta_units": format_integer_column("Δ unidades"),
                "revenue": format_currency_column(f"Ventas ({filters.currency_label})"),
                "delta_revenue": format_currency_column("Δ ventas"),
                "delta_pct": st.column_config.NumberColumn("Δ %", format="%,.2f%%"),
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

    st.dataframe(
        brand_summary.sort_values("delta_revenue", ascending=False).head(12),
        use_container_width=True,
        height=table_height(12),
        column_config={
            "BRAND": "Marca",
            "units": format_integer_column("Unidades"),
            "revenue": format_currency_column(f"Ventas ({filters.currency_label})"),
            "prev_revenue": format_currency_column("Periodo anterior"),
            "delta_revenue": format_currency_column("Δ ventas"),
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
