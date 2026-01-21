from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Iterable

import pandas as pd
from dbfread import DBF


@dataclass
class DataBundle:
    invoices: pd.DataFrame
    invoice_lines: pd.DataFrame
    products: pd.DataFrame
    clients: pd.DataFrame
    sellers: pd.DataFrame
    stock: pd.DataFrame
    orders: pd.DataFrame
    pedidos: pd.DataFrame


def _read_dbf(path: Path) -> pd.DataFrame:
    """Read a DBF file into a DataFrame, returning empty if missing."""
    if not path.exists():
        return pd.DataFrame()
    table = DBF(path, load=True, char_decode_errors="ignore")
    df = pd.DataFrame(iter(table))
    for col in ("INV_DATE", "ORD_DATE"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
    return df


def _first_existing(dbf_dir: Path, names: Iterable[str]) -> Path | None:
    for name in names:
        path = dbf_dir / name
        if path.exists():
            return path
    return None


def _ensure_numeric(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denom = denominator.replace(0, pd.NA)
    result = numerator / denom
    return result.fillna(0)


def load_bundle(dbf_dir: Path) -> DataBundle:
    """Load DBF sources into a DataBundle.

    Supports the newer mock schema (PRODUCTS/CLIENTS/SELLERS/INVOICES/INVOICE_LINES/STOCK/PEDIDOS).
    """
    products_path = _first_existing(dbf_dir, ["PRODUCTS.DBF", "PRODUCTOS.DBF"])
    clients_path = _first_existing(dbf_dir, ["CLIENTS.DBF", "CLIENTES.DBF"])
    sellers_path = _first_existing(dbf_dir, ["SELLERS.DBF", "VENDEDORES.DBF"])
    invoices_path = _first_existing(dbf_dir, ["INVOICES.DBF", "VENTAS.DBF"])
    invoice_lines_path = _first_existing(dbf_dir, ["INVOICE_LINES.DBF"])
    stock_path = _first_existing(dbf_dir, ["STOCK.DBF"])
    orders_path = _first_existing(dbf_dir, ["PEDIDOS.DBF"])

    products = _read_dbf(products_path) if products_path else pd.DataFrame()
    clients = _read_dbf(clients_path) if clients_path else pd.DataFrame()
    sellers = _read_dbf(sellers_path) if sellers_path else pd.DataFrame()
    invoices = _read_dbf(invoices_path) if invoices_path else pd.DataFrame()
    invoice_lines = _read_dbf(invoice_lines_path) if invoice_lines_path else pd.DataFrame()
    stock = _read_dbf(stock_path) if stock_path else pd.DataFrame()
    orders = _read_dbf(orders_path) if orders_path else pd.DataFrame()

    return DataBundle(
        invoices=invoices,
        invoice_lines=invoice_lines,
        products=products,
        clients=clients,
        sellers=sellers,
        stock=stock,
        orders=orders,
        pedidos=orders,
    )


def enrich_sales(bundle: DataBundle) -> pd.DataFrame:
    """Build sales dataset from invoices and invoice lines."""
    if bundle.invoice_lines.empty or bundle.invoices.empty:
        return pd.DataFrame()

    ventas = bundle.invoice_lines.copy()
    ventas = ventas.merge(bundle.invoices, on="INV_ID", how="left", suffixes=("", "_INV"))
    if not bundle.products.empty:
        ventas = ventas.merge(bundle.products, on="PROD_ID", how="left", suffixes=("", "_PROD"))
    if not bundle.clients.empty:
        ventas = ventas.merge(bundle.clients, on="CL_ID", how="left", suffixes=("", "_CLI"))
    if not bundle.sellers.empty:
        ventas = ventas.merge(bundle.sellers, on="SELLER_ID", how="left", suffixes=("", "_SELL"))

    ventas = _ensure_numeric(ventas, ["QTY", "UNIT_PRICE", "FX"])
    ventas["QTY"] = ventas["QTY"].fillna(0)
    ventas["UNIT_PRICE"] = ventas["UNIT_PRICE"].fillna(0)
    ventas["FX"] = ventas["FX"].fillna(1).replace(0, 1)

    ventas["AMOUNT"] = ventas["QTY"] * ventas["UNIT_PRICE"]
    currency = ventas.get("CURRENCY", pd.Series(["MXN"] * len(ventas))).astype(str).str.upper()
    is_usd = currency.eq("USD")

    ventas["AMOUNT_MXN"] = ventas["AMOUNT"] * ventas["FX"].where(is_usd, 1)
    ventas["AMOUNT_USD"] = ventas["AMOUNT"].where(is_usd, _safe_divide(ventas["AMOUNT"], ventas["FX"]))

    ventas["SALE_ID"] = ventas["INV_ID"]
    ventas["SALE_DATE"] = ventas["INV_DATE"]
    ventas["QUANTITY"] = ventas["QTY"]
    ventas["TOTAL_MXN"] = ventas["AMOUNT_MXN"]
    ventas["TOTAL_USD"] = ventas["AMOUNT_USD"]
    ventas["CLIENT_NAME"] = ventas.get("CL_NAME")
    ventas["PRODUCT_ID"] = ventas.get("PROD_ID")
    ventas["PRODUCT_NAME"] = ventas.get("PROD_NAME")
    ventas["VENDOR_NAME"] = ventas.get("SELLER_NAME")

    if "SALE_DATE" in ventas.columns:
        ventas["WEEK"] = ventas["SALE_DATE"].dt.isocalendar().week.astype(int)

    return ventas


def filter_sales(
    ventas: pd.DataFrame,
    date_range: tuple[pd.Timestamp, pd.Timestamp] | None,
    brands: list[str],
    vendors: list[str],
    weeks: list[int] | None = None,
) -> pd.DataFrame:
    """Apply global filters to the sales dataset."""
    df = ventas.copy()
    if df.empty:
        return df
    if date_range:
        start, end = date_range
        df = df[(df["SALE_DATE"] >= start) & (df["SALE_DATE"] <= end)]
    if brands and "BRAND" in df.columns:
        df = df[df["BRAND"].isin(brands)]
    if vendors and "VENDOR_NAME" in df.columns:
        df = df[df["VENDOR_NAME"].isin(vendors)]
    if weeks and "WEEK" in df.columns:
        df = df[df["WEEK"].isin(weeks)]
    return df


def build_product_kpis(ventas: pd.DataFrame, bundle: DataBundle) -> dict[str, pd.DataFrame]:
    """Compute product KPIs (rotation, inventory value, pareto, monthly stock view)."""
    products = bundle.products.copy() if not bundle.products.empty else pd.DataFrame()
    stock = bundle.stock.copy() if not bundle.stock.empty else pd.DataFrame()

    if not products.empty:
        products = products.rename(columns={"PROD_ID": "PRODUCT_ID", "PROD_NAME": "PRODUCT_NAME"})
    if not stock.empty:
        stock = stock.rename(columns={"PROD_ID": "PRODUCT_ID"})

    productos = products.merge(stock, on="PRODUCT_ID", how="left") if not products.empty else pd.DataFrame()
    if not productos.empty:
        productos = _ensure_numeric(productos, ["PRICE", "ON_HAND"]).fillna({"ON_HAND": 0, "PRICE": 0})
        productos["INVENTORY_VALUE_MXN"] = productos["ON_HAND"] * productos["PRICE"]

    ventas_prod = ventas.groupby("PRODUCT_ID", as_index=False).agg(
        SOLD_UNITS=("QUANTITY", "sum"),
        SOLD_MXN=("AMOUNT_MXN", "sum"),
    )

    if not productos.empty:
        productos = productos.merge(ventas_prod, on="PRODUCT_ID", how="left").fillna({"SOLD_UNITS": 0, "SOLD_MXN": 0})
        productos["ROTATION"] = _safe_divide(productos["SOLD_UNITS"], productos["ON_HAND"])

    pareto = productos.sort_values(by="SOLD_UNITS", ascending=False).head(10) if not productos.empty else pd.DataFrame()

    sales_month = pd.DataFrame()
    if not ventas.empty:
        last_date = ventas["SALE_DATE"].max()
        start_date = last_date - timedelta(days=30)
        monthly = ventas[(ventas["SALE_DATE"] >= start_date) & (ventas["SALE_DATE"] <= last_date)]
        sales_month = monthly.groupby("PRODUCT_ID", as_index=False).agg(
            SALES_MONTH_UNITS=("QUANTITY", "sum"),
            SALES_MONTH_MXN=("AMOUNT_MXN", "sum"),
        )

    stock_sales = productos.merge(sales_month, on="PRODUCT_ID", how="left") if not productos.empty else pd.DataFrame()
    if not stock_sales.empty:
        stock_sales = stock_sales.fillna({"SALES_MONTH_UNITS": 0, "SALES_MONTH_MXN": 0})
        stock_sales = stock_sales.sort_values(by="SALES_MONTH_UNITS", ascending=False)

    rotation_table = productos[["PRODUCT_NAME", "ROTATION", "SOLD_UNITS", "SOLD_MXN", "ON_HAND"]].copy() if not productos.empty else pd.DataFrame()

    return {
        "products": productos,
        "pareto": pareto,
        "stock_sales": stock_sales,
        "rotation_table": rotation_table,
    }


def build_client_kpis(ventas: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Compute client KPIs and origin summaries."""
    if ventas.empty:
        return {"clients": pd.DataFrame(), "origin": pd.DataFrame()}

    clientes = ventas.groupby("CLIENT_NAME", as_index=False).agg(
        TOTAL_MXN=("AMOUNT_MXN", "sum"),
        TOTAL_USD=("AMOUNT_USD", "sum"),
        INVOICES=("SALE_ID", "nunique"),
        LAST_PURCHASE=("SALE_DATE", "max"),
        ORIGIN=("ORIGIN", "first"),
    )
    clientes["AVG_TICKET_MXN"] = _safe_divide(clientes["TOTAL_MXN"], clientes["INVOICES"])
    clientes = clientes.sort_values(by="TOTAL_MXN", ascending=False)

    origin_summary = ventas.groupby("ORIGIN", as_index=False).agg(
        CLIENTS=("CLIENT_ID", "nunique"),
        INVOICES=("SALE_ID", "nunique"),
        AMOUNT_MXN=("AMOUNT_MXN", "sum"),
        AMOUNT_USD=("AMOUNT_USD", "sum"),
    )

    return {"clients": clientes, "origin": origin_summary}


def build_client_cards(ventas: pd.DataFrame) -> dict[str, int]:
    """Return client card metrics for MXN/USD billed customers."""
    if ventas.empty:
        return {"clients_mxn": 0, "clients_usd": 0, "clients_total": 0}
    clients_mxn = ventas[ventas["AMOUNT_MXN"] > 0]["CLIENT_ID"].nunique()
    clients_usd = ventas[ventas["AMOUNT_USD"] > 0]["CLIENT_ID"].nunique()
    clients_total = ventas["CLIENT_ID"].nunique()
    return {
        "clients_mxn": int(clients_mxn),
        "clients_usd": int(clients_usd),
        "clients_total": int(clients_total),
    }


def build_sales_agent_kpis(
    ventas: pd.DataFrame,
    date_range: tuple[pd.Timestamp, pd.Timestamp] | None = None,
) -> pd.DataFrame:
    """Compute seller totals and daily averages in MXN."""
    if ventas.empty:
        return pd.DataFrame()

    if date_range:
        start, end = date_range
    else:
        start, end = ventas["SALE_DATE"].min(), ventas["SALE_DATE"].max()

    business_days = len(pd.bdate_range(start=start, end=end)) or 1

    ventas_agente = ventas.groupby("VENDOR_NAME", as_index=False).agg(
        TOTAL_MXN=("AMOUNT_MXN", "sum"),
        INVOICES=("SALE_ID", "nunique"),
    )
    ventas_agente["DAILY_AVG_MXN"] = ventas_agente["TOTAL_MXN"] / business_days
    return ventas_agente.sort_values(by="TOTAL_MXN", ascending=False)


def build_sales_timeseries(ventas: pd.DataFrame, granularity: str) -> pd.DataFrame:
    """Return sales time series by seller for daily/weekly/monthly granularities."""
    if ventas.empty:
        return pd.DataFrame()

    ventas_time = ventas.copy()
    if granularity == "Semanal":
        ventas_time["PERIOD"] = ventas_time["SALE_DATE"].dt.to_period("W").dt.start_time
    elif granularity == "Mensual":
        ventas_time["PERIOD"] = ventas_time["SALE_DATE"].dt.to_period("M").dt.start_time
    else:
        ventas_time["PERIOD"] = ventas_time["SALE_DATE"].dt.date

    return (
        ventas_time.groupby(["PERIOD", "VENDOR_NAME"], as_index=False)["AMOUNT_MXN"].sum()
    )


def build_order_cards(
    orders: pd.DataFrame,
    date_range: tuple[pd.Timestamp, pd.Timestamp] | None,
    granularity: str,
) -> dict[str, float]:
    """Compute order cards: total billing, order trend and pending orders."""
    if orders.empty:
        return {"total_mxn": 0.0, "order_trend": 0.0, "pending_orders": 0}

    if date_range:
        start, end = date_range
    else:
        start, end = orders["ORD_DATE"].min(), orders["ORD_DATE"].max()

    orders_range = orders[(orders["ORD_DATE"] >= start) & (orders["ORD_DATE"] <= end)]
    total_mxn = orders_range["TOTAL_ESTIMADO"].sum() if "TOTAL_ESTIMADO" in orders_range.columns else 0.0

    if granularity == "Mensual":
        delta = (end - start) + timedelta(days=1)
        prev_start = start - delta
        prev_end = start - timedelta(days=1)
    else:
        delta = (end - start) + timedelta(days=1)
        prev_start = start - delta
        prev_end = start - timedelta(days=1)

    prev_orders = orders[(orders["ORD_DATE"] >= prev_start) & (orders["ORD_DATE"] <= prev_end)]
    order_trend = orders_range["ORD_ID"].nunique() - prev_orders["ORD_ID"].nunique()

    pending_orders = orders_range[orders_range["STATUS"].astype(str).str.upper().eq("SURTIR")]["ORD_ID"].nunique()

    return {
        "total_mxn": float(total_mxn),
        "order_trend": float(order_trend),
        "pending_orders": int(pending_orders),
    }
