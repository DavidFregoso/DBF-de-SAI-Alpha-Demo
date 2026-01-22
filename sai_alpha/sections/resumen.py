from __future__ import annotations

from datetime import timedelta

import pandas as pd
import plotly.express as px
import streamlit as st

from sai_alpha.etl import resolve_dbf_dir
from sai_alpha.formatting import fmt_currency, fmt_int, fmt_num, fmt_percent
from sai_alpha.filters import FilterState
from sai_alpha.schema import canonicalize_products, coalesce_column
from sai_alpha.ui import (
    build_time_series,
    export_buttons,
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
    col1.metric(f"Ventas ({filters.currency_label})", fmt_currency(revenue, filters.currency_label))
    col2.metric("Unidades", fmt_int(units))
    col3.metric("Pedidos", fmt_int(orders))
    col4.metric("Clientes activos", fmt_int(clients))
    col5.metric(
        "FX promedio",
        f"{fmt_num(filters.fx_average)} MXN/USD" if filters.fx_average else "N/D",
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
    low_stock = inventory.sort_values("DAYS_INVENTORY").head(10)
    overstock = inventory.sort_values("DAYS_INVENTORY", ascending=False).head(10)

    required_inventory_columns = {"PRODUCT_NAME", "BRAND", "CATEGORY", "STOCK_QTY", "DAYS_INVENTORY"}
    missing_inventory_columns = sorted(required_inventory_columns - set(low_stock.columns))
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
        low_display = low_stock.assign(
            STOCK_QTY_FMT=low_stock["STOCK_QTY"].map(fmt_int),
            DAYS_INVENTORY_FMT=low_stock["DAYS_INVENTORY"].map(fmt_num),
        )
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
        st.markdown("**Sobre-stock (días altos)**")
        over_display = overstock.assign(
            STOCK_QTY_FMT=overstock["STOCK_QTY"].map(fmt_int),
            DAYS_INVENTORY_FMT=overstock["DAYS_INVENTORY"].map(fmt_num),
        )
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
        brand_gain = brand_delta.sort_values("delta", ascending=False).head(8).copy()
        brand_gain["current_revenue_fmt"] = brand_gain["current_revenue"].map(
            lambda value: fmt_currency(value, filters.currency_label)
        )
        brand_gain["prev_revenue_fmt"] = brand_gain["prev_revenue"].map(
            lambda value: fmt_currency(value, filters.currency_label)
        )
        brand_gain["delta_fmt"] = brand_gain["delta"].map(
            lambda value: fmt_currency(value, filters.currency_label)
        )
        brand_gain["delta_pct_fmt"] = brand_gain["delta_pct"].map(fmt_percent)
        st.dataframe(
            brand_gain[["BRAND", "current_revenue_fmt", "prev_revenue_fmt", "delta_fmt", "delta_pct_fmt"]],
            use_container_width=True,
            height=table_height(8),
            column_config={
                "BRAND": "Marca",
                "current_revenue_fmt": st.column_config.TextColumn(
                    f"Ventas ({filters.currency_label})"
                ),
                "prev_revenue_fmt": st.column_config.TextColumn("Periodo anterior"),
                "delta_fmt": st.column_config.TextColumn("Δ ventas"),
                "delta_pct_fmt": st.column_config.TextColumn("Δ %"),
            },
        )
    with col_loss:
        st.markdown("**Marcas con mayor caída**")
        brand_loss = brand_delta.sort_values("delta", ascending=True).head(8).copy()
        brand_loss["current_revenue_fmt"] = brand_loss["current_revenue"].map(
            lambda value: fmt_currency(value, filters.currency_label)
        )
        brand_loss["prev_revenue_fmt"] = brand_loss["prev_revenue"].map(
            lambda value: fmt_currency(value, filters.currency_label)
        )
        brand_loss["delta_fmt"] = brand_loss["delta"].map(
            lambda value: fmt_currency(value, filters.currency_label)
        )
        brand_loss["delta_pct_fmt"] = brand_loss["delta_pct"].map(fmt_percent)
        st.dataframe(
            brand_loss[["BRAND", "current_revenue_fmt", "prev_revenue_fmt", "delta_fmt", "delta_pct_fmt"]],
            use_container_width=True,
            height=table_height(8),
            column_config={
                "BRAND": "Marca",
                "current_revenue_fmt": st.column_config.TextColumn(
                    f"Ventas ({filters.currency_label})"
                ),
                "prev_revenue_fmt": st.column_config.TextColumn("Periodo anterior"),
                "delta_fmt": st.column_config.TextColumn("Δ ventas"),
                "delta_pct_fmt": st.column_config.TextColumn("Δ %"),
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
        col1.metric("Pedidos pendientes", fmt_int(pending_count))
        col2.metric(
            "Valor pendiente (estimado)", fmt_currency(pending_value, filters.currency_label)
        )

        pending_vendor = pending.groupby("SELLER_NAME").agg(
            pedidos=("ORDER_ID", "nunique"),
            valor=("PENDING_VALUE", "sum"),
        )
        pending_vendor = pending_vendor.reset_index().sort_values("valor", ascending=False).head(10)
        pending_vendor["pedidos_fmt"] = pending_vendor["pedidos"].map(fmt_int)
        pending_vendor["valor_fmt"] = pending_vendor["valor"].map(
            lambda value: fmt_currency(value, filters.currency_label)
        )
        st.dataframe(
            pending_vendor[["SELLER_NAME", "pedidos_fmt", "valor_fmt"]],
            use_container_width=True,
            height=table_height(len(pending_vendor)),
            column_config={
                "SELLER_NAME": "Vendedor",
                "pedidos_fmt": st.column_config.TextColumn("Pedidos"),
                "valor_fmt": st.column_config.TextColumn("Valor pendiente"),
            },
        )

    st.divider()
    st.markdown("### Exportar")
    export_buttons(filtered, "resumen_ventas")
