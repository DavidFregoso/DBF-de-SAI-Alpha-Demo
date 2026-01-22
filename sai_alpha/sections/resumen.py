from __future__ import annotations

from datetime import timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from sai_alpha.etl import resolve_dbf_dir
from sai_alpha.filters import FilterState
from sai_alpha.ui import (
    build_time_series,
    export_buttons,
    format_currency_column,
    format_integer_column,
    format_int,
    format_money,
    format_number_column,
    render_page_header,
    normalize_currency,
    plotly_colors,
    table_height,
)


def render(filters: FilterState, bundle, ventas: pd.DataFrame, pedidos: pd.DataFrame | None) -> None:
    render_page_header("Resumen Ejecutivo")

    filtered = filters.sales
    if filtered.empty:
        st.warning("No hay registros con los filtros actuales.")
        return

    revenue = filtered[filters.revenue_column].sum()
    units = filtered["QTY"].sum()
    orders = (
        filtered["FACTURA_ID"].nunique()
        if "FACTURA_ID" in filtered.columns
        else filtered["SALE_ID"].nunique()
    )
    clients = filtered["CLIENT_ID"].nunique()

    st.markdown("### KPIs clave")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric(f"Ventas ({filters.currency_label})", f"$ {format_money(revenue)}")
    col2.metric("Unidades", format_int(units))
    col3.metric("Pedidos", format_int(orders))
    col4.metric("Clientes activos", format_int(clients))
    col5.metric(
        "FX promedio",
        f"{format_money(filters.fx_average)} MXN/USD" if filters.fx_average else "N/D",
    )

    st.divider()
    st.markdown("### Panorama de ventas")
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
    st.markdown("### Inventario crítico y sobre-stock")
    period_days = max(1, (filters.end_date - filters.start_date).days + 1)
    product_sales = (
        filtered.groupby(["PRODUCT_ID", "PRODUCT_NAME", "BRAND", "CATEGORY"])
        .agg(units=("QTY", "sum"), revenue=(filters.revenue_column, "sum"))
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
    low_stock = inventory.sort_values("DAYS_INVENTORY").head(10)
    overstock = inventory.sort_values("DAYS_INVENTORY", ascending=False).head(10)

    required_inventory_columns = ["PRODUCT_NAME", "BRAND", "CATEGORY", "STOCK_QTY", "DAYS_INVENTORY"]
    missing_inventory_columns = [col for col in required_inventory_columns if col not in low_stock.columns]
    if missing_inventory_columns:
        st.error(
            "Faltan columnas requeridas para 'Productos por agotarse': "
            + ", ".join(missing_inventory_columns)
        )
        dbf_path = resolve_dbf_dir() / "productos.dbf"
        st.write("Fuente DBF:", str(dbf_path))
        st.write("Columnas normalizadas:", list(inventory.columns))
        st.write("Columnas disponibles:", list(low_stock.columns))
        return

    col_low, col_high = st.columns(2)
    with col_low:
        st.markdown("**Productos por agotarse**")
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
    with col_high:
        st.markdown("**Sobre-stock (días altos)**")
        st.dataframe(
            overstock[["PRODUCT_NAME", "BRAND", "CATEGORY", "STOCK_QTY", "DAYS_INVENTORY"]],
            use_container_width=True,
            height=table_height(len(overstock)),
            column_config={
                "PRODUCT_NAME": "Producto",
                "BRAND": "Marca",
                "CATEGORY": "Categoría",
                "STOCK_QTY": format_integer_column("Existencia"),
                "DAYS_INVENTORY": format_number_column("Días inventario"),
            },
        )

    st.divider()
    st.markdown("### Marcas dominantes por volumen y facturación")
    brand_units = (
        filtered.groupby("BRAND")
        .agg(units=("QTY", "sum"), revenue=(filters.revenue_column, "sum"))
        .reset_index()
    )
    col_units, col_revenue = st.columns(2)
    with col_units:
        top_units = brand_units.sort_values("units", ascending=False).head(8)
        fig_units = px.bar(
            top_units,
            x="units",
            y="BRAND",
            orientation="h",
            title="Top marcas por unidades",
            color_discrete_sequence=plotly_colors(),
        )
        fig_units.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_units, use_container_width=True)
    with col_revenue:
        top_revenue = brand_units.sort_values("revenue", ascending=False).head(8)
        fig_revenue = px.bar(
            top_revenue,
            x="revenue",
            y="BRAND",
            orientation="h",
            title=f"Top marcas por ventas ({filters.currency_label})",
            color_discrete_sequence=plotly_colors(),
        )
        fig_revenue.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_revenue, use_container_width=True)

    st.divider()
    st.markdown("### Cambios vs periodo anterior")
    period_days = max(1, (filters.end_date - filters.start_date).days + 1)
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

    current_brand = (
        filtered.groupby("BRAND")[filters.revenue_column].sum().reset_index(name="current_revenue")
    )
    previous_brand = (
        prev_sales.groupby("BRAND")[filters.revenue_column].sum().reset_index(name="prev_revenue")
    )
    brand_delta = current_brand.merge(previous_brand, on="BRAND", how="left").fillna(0.0)
    brand_delta["delta"] = brand_delta["current_revenue"] - brand_delta["prev_revenue"]
    brand_delta["delta_pct"] = brand_delta.apply(
        lambda row: (row["delta"] / row["prev_revenue"] * 100) if row["prev_revenue"] > 0 else 0.0,
        axis=1,
    )

    col_gain, col_loss = st.columns(2)
    with col_gain:
        st.markdown("**Marcas con mayor crecimiento**")
        st.dataframe(
            brand_delta.sort_values("delta", ascending=False).head(8),
            use_container_width=True,
            height=table_height(8),
            column_config={
                "BRAND": "Marca",
                "current_revenue": format_currency_column(f"Ventas ({filters.currency_label})"),
                "prev_revenue": format_currency_column("Periodo anterior"),
                "delta": format_currency_column("Δ ventas"),
                "delta_pct": st.column_config.NumberColumn("Δ %", format="%,.2f%%"),
            },
        )
    with col_loss:
        st.markdown("**Marcas con mayor caída**")
        st.dataframe(
            brand_delta.sort_values("delta", ascending=True).head(8),
            use_container_width=True,
            height=table_height(8),
            column_config={
                "BRAND": "Marca",
                "current_revenue": format_currency_column(f"Ventas ({filters.currency_label})"),
                "prev_revenue": format_currency_column("Periodo anterior"),
                "delta": format_currency_column("Δ ventas"),
                "delta_pct": st.column_config.NumberColumn("Δ %", format="%,.2f%%"),
            },
        )

    st.divider()
    st.markdown("### Pedidos por surtir (resumen)")
    if filters.pedidos is None or filters.pedidos.empty:
        st.info("No hay pedidos cargados.")
    else:
        pending = filters.pedidos[filters.pedidos["STATUS"].isin(["Pendiente", "Parcial"])].copy()
        pending["PENDING_VALUE"] = pending["QTY_PENDING"] * pending["PRICE_MXN"].fillna(0)
        pending_count = pending["ORDER_ID"].nunique()
        pending_value = pending["PENDING_VALUE"].sum()

        col1, col2 = st.columns(2)
        col1.metric("Pedidos pendientes", format_int(pending_count))
        col2.metric("Valor pendiente (estimado)", f"$ {format_money(pending_value)}")

        pending_vendor = pending.groupby("SELLER_NAME").agg(
            pedidos=("ORDER_ID", "nunique"),
            valor=("PENDING_VALUE", "sum"),
        )
        pending_vendor = pending_vendor.reset_index().sort_values("valor", ascending=False).head(10)
        st.dataframe(
            pending_vendor,
            use_container_width=True,
            height=table_height(len(pending_vendor)),
            column_config={
                "SELLER_NAME": "Vendedor",
                "pedidos": format_integer_column("Pedidos"),
                "valor": format_currency_column("Valor pendiente"),
            },
        )

    st.divider()
    st.markdown("### Exportar")
    export_buttons(filtered, "resumen_ventas")
