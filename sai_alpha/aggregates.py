from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd
import streamlit as st

from sai_alpha.perf import perf_logger
from sai_alpha.schema import canonicalize_products, require_columns, resolve_column
from sai_alpha.ui import build_time_series


def _safe_column(df: pd.DataFrame, col: str, default: Any = 0) -> pd.Series:
    if col in df.columns:
        return df[col]
    return pd.Series([default] * len(df), index=df.index)


@st.cache_data(show_spinner=False)
def build_aggregates(
    ventas: pd.DataFrame,
    ventas_filtradas: pd.DataFrame,
    pedidos_filtrados: pd.DataFrame | None,
    productos_filtrados: pd.DataFrame,
    start_date: date,
    end_date: date,
    revenue_column: str,
    currency_label: str,
    granularity: str,
    filter_key: str,
) -> dict[str, Any]:
    with perf_logger("build_aggregates"):
        aggregates: dict[str, Any] = {}

        sales = ventas_filtradas
        order_column = "FACTURA_ID" if "FACTURA_ID" in sales.columns else "SALE_ID"
        revenue_series = _safe_column(sales, revenue_column, default=0)
        qty_series = _safe_column(sales, "QTY", default=0)

        orders_count = sales[order_column].nunique() if order_column in sales.columns else 0
        clients_count = sales["CLIENT_ID"].nunique() if "CLIENT_ID" in sales.columns else 0
        revenue_total = float(revenue_series.sum())
        ticket = revenue_total / orders_count if orders_count else 0

        aggregates["kpi_sales"] = {
            "revenue": revenue_total,
            "orders": int(orders_count),
            "clients": int(clients_count),
            "ticket": ticket,
            "currency_label": currency_label,
        }

        aggregates["ventas_by_period"] = build_time_series(sales, "SALE_DATE", revenue_column, granularity)

        if "ORIGEN_VENTA" in sales.columns:
            aggregates["ventas_by_channel"] = (
                sales.groupby("ORIGEN_VENTA")[revenue_column].sum().reset_index()
            )
        else:
            aggregates["ventas_by_channel"] = pd.DataFrame(columns=["ORIGEN_VENTA", revenue_column])

        if "BRAND" in sales.columns:
            aggregates["ventas_by_brand"] = (
                sales.groupby("BRAND")[revenue_column].sum().reset_index()
            )
        else:
            aggregates["ventas_by_brand"] = pd.DataFrame(columns=["BRAND", revenue_column])

        invoice_group_cols = [
            col
            for col in [
                order_column,
                "SALE_DATE",
                "CLIENT_NAME",
                "SELLER_NAME",
                "CURRENCY",
                "STATUS",
            ]
            if col in sales.columns
        ]
        if invoice_group_cols:
            aggregates["invoice_table"] = (
                sales.groupby(invoice_group_cols)
                .agg(revenue=(revenue_column, "sum"), units=("QTY", "sum"))
                .reset_index()
                .sort_values("revenue", ascending=False)
            )
        else:
            aggregates["invoice_table"] = pd.DataFrame()

        product_col = resolve_column(sales, ["PRODUCT_NAME", "PRODUCT_NAME_X", "PRODUCT_NAME_Y"])
        if product_col:
            aggregates["top_products"] = (
                sales.groupby(product_col)
                .agg(units=("QTY", "sum"), revenue=(revenue_column, "sum"))
                .reset_index()
                .sort_values("revenue", ascending=False)
                .head(10)
            )
        else:
            aggregates["top_products"] = pd.DataFrame()

        if "CLIENT_NAME" in sales.columns:
            aggregates["top_clients"] = (
                sales.groupby("CLIENT_NAME")
                .agg(revenue=(revenue_column, "sum"))
                .reset_index()
                .sort_values("revenue", ascending=False)
                .head(10)
            )
        else:
            aggregates["top_clients"] = pd.DataFrame()

        if "CLIENT_ID" in ventas.columns and "SALE_DATE" in ventas.columns:
            first_purchase = ventas.groupby("CLIENT_ID")["SALE_DATE"].min().reset_index(name="first_purchase")
            active_clients = sales[["CLIENT_ID"]].drop_duplicates()
            active_clients = active_clients.merge(first_purchase, on="CLIENT_ID", how="left")
            new_clients = int((active_clients["first_purchase"] >= pd.Timestamp(start_date)).sum())
            recurrent_clients = max(0, len(active_clients) - new_clients)
        else:
            new_clients = 0
            recurrent_clients = 0

        aggregates["clientes_kpi"] = {
            "new_clients": new_clients,
            "recurrent_clients": recurrent_clients,
            "mxn_count": int((sales["CURRENCY"] == "MXN").sum()) if "CURRENCY" in sales.columns else 0,
            "usd_count": int((sales["CURRENCY"] == "USD").sum()) if "CURRENCY" in sales.columns else 0,
        }

        if "CLIENT_NAME" in sales.columns and "CLIENT_ID" in sales.columns:
            invoice_col = "FACTURA_ID" if "FACTURA_ID" in sales.columns else "SALE_ID"
            aggregates["clientes_summary"] = (
                sales.groupby(["CLIENT_ID", "CLIENT_NAME"])
                .agg(
                    revenue=(revenue_column, "sum"),
                    units=("QTY", "sum"),
                    invoices=(invoice_col, "nunique"),
                    last_order=("SALE_DATE", "max"),
                )
                .reset_index()
                .sort_values("revenue", ascending=False)
            )
        else:
            aggregates["clientes_summary"] = pd.DataFrame()

        if "CLIENT_ORIGIN" in sales.columns and "CLIENT_ID" in sales.columns:
            aggregates["clientes_origin"] = (
                sales.groupby("CLIENT_ORIGIN")["CLIENT_ID"].nunique().reset_index(name="Clientes")
            )
        else:
            aggregates["clientes_origin"] = pd.DataFrame(columns=["CLIENT_ORIGIN", "Clientes"])

        if "SELLER_NAME" in sales.columns:
            seller_summary = (
                sales.groupby("SELLER_NAME")
                .agg(
                    revenue=(revenue_column, "sum"),
                    units=("QTY", "sum"),
                    orders=(order_column, "nunique") if order_column in sales.columns else ("QTY", "size"),
                )
                .reset_index()
                .sort_values("revenue", ascending=False)
            )
            aggregates["seller_summary"] = seller_summary
            if "SALE_DATE" in sales.columns:
                aggregates["seller_trend"] = (
                    sales.groupby(["SELLER_NAME", pd.Grouper(key="SALE_DATE", freq="W-MON")])[
                        revenue_column
                    ]
                    .sum()
                    .reset_index()
                )
            else:
                aggregates["seller_trend"] = pd.DataFrame()
        else:
            aggregates["seller_summary"] = pd.DataFrame()
            aggregates["seller_trend"] = pd.DataFrame()

        inventory = canonicalize_products(productos_filtrados)
        inventory_ok, missing_cols = require_columns(
            inventory, {"PRODUCT_ID", "PRODUCT_NAME", "STOCK_QTY", "COST_MXN"}
        )
        if inventory_ok:
            period_days = max(1, (end_date - start_date).days + 1)
            if "PRODUCT_ID" in sales.columns:
                sales_summary = sales.groupby("PRODUCT_ID").agg(units=("QTY", "sum")).reset_index()
                sales_summary["avg_daily_units"] = sales_summary["units"] / period_days
                inventory = inventory.merge(sales_summary, on="PRODUCT_ID", how="left")
                inventory["units"] = inventory["units"].fillna(0)
                inventory["avg_daily_units"] = inventory["avg_daily_units"].fillna(0)
            else:
                inventory["units"] = 0
                inventory["avg_daily_units"] = 0
            inventory["DAYS_INVENTORY"] = inventory["STOCK_QTY"] / inventory["avg_daily_units"].replace(0, pd.NA)
            inventory["inventory_value"] = inventory["STOCK_QTY"].fillna(0) * inventory["COST_MXN"].fillna(0)
        else:
            inventory = pd.DataFrame(columns=list(inventory.columns))
        aggregates["inventory_summary"] = inventory
        aggregates["inventory_missing"] = missing_cols

        if not inventory.empty:
            if "MIN_STOCK" not in inventory.columns:
                inventory["MIN_STOCK"] = inventory["STOCK_QTY"].fillna(0) * 0.2
            if "MAX_STOCK" not in inventory.columns:
                inventory["MAX_STOCK"] = inventory["STOCK_QTY"].fillna(0) * 1.6
            low_stock = inventory[inventory["STOCK_QTY"] <= inventory["MIN_STOCK"]]
            over_stock = inventory[inventory["STOCK_QTY"] >= inventory["MAX_STOCK"]]
        else:
            low_stock = pd.DataFrame()
            over_stock = pd.DataFrame()
        aggregates["inventory_low"] = low_stock
        aggregates["inventory_over"] = over_stock

        if pedidos_filtrados is not None and not pedidos_filtrados.empty:
            pending = pedidos_filtrados[pedidos_filtrados["STATUS"].isin(["Pendiente", "Parcial"])].copy()
            pending["PENDING_VALUE"] = pending["QTY_PENDING"].fillna(0) * pending["PRICE_MXN"].fillna(0)
            aggregates["pedidos_pending"] = pending
            if "ORDER_DATE" in pending.columns:
                aggregates["pedidos_weekly"] = (
                    pending.groupby(pd.Grouper(key="ORDER_DATE", freq="W-MON"))["PENDING_VALUE"]
                    .sum()
                    .reset_index()
                )
            else:
                aggregates["pedidos_weekly"] = pd.DataFrame(columns=["ORDER_DATE", "PENDING_VALUE"])
        else:
            aggregates["pedidos_pending"] = pd.DataFrame()
            aggregates["pedidos_weekly"] = pd.DataFrame()

        return aggregates
