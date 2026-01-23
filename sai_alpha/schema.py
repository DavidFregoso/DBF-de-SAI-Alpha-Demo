from __future__ import annotations

import re
from typing import Iterable

import pandas as pd


DEFAULT_TEXT = "No disponible"


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    normalized = []
    for column in df.columns:
        cleaned = re.sub(r"[^0-9A-Za-z_]+", "_", str(column).strip().upper())
        cleaned = re.sub(r"_+", "_", cleaned).strip("_")
        normalized.append(cleaned)
    df.columns = normalized
    return df


def coalesce_columns(
    df: pd.DataFrame,
    target: str,
    candidates: Iterable[str],
    default: object | None = None,
    drop_candidates: bool = False,
) -> pd.DataFrame:
    df = df.copy()
    if target not in df.columns:
        df[target] = pd.NA
    for candidate in candidates:
        if candidate in df.columns:
            df[target] = df[target].where(df[target].notna(), df[candidate])
    if default is not None:
        df[target] = df[target].fillna(default)
    if drop_candidates:
        for candidate in candidates:
            if candidate != target and candidate in df.columns:
                df = df.drop(columns=candidate)
    return df


def require_columns(df: pd.DataFrame, cols: Iterable[str]) -> tuple[bool, list[str]]:
    missing = sorted(set(cols) - set(df.columns))
    return (len(missing) == 0, missing)


def resolve_column(
    df: pd.DataFrame,
    candidates: Iterable[str],
    required: bool = False,
) -> str | None:
    for candidate in candidates:
        if candidate in df.columns:
            return candidate
    return None if required else None


def coalesce_column(
    df: pd.DataFrame,
    target: str,
    candidates: Iterable[str],
    drop_candidates: bool = True,
) -> pd.DataFrame:
    return coalesce_columns(df, target, candidates, drop_candidates=drop_candidates)


def canonicalize_products(df_products: pd.DataFrame) -> pd.DataFrame:
    df = normalize_columns(df_products)
    df = coalesce_columns(df, "SKU", ["SKU", "CODIGO", "COD_PRODUCTO"], default="")
    df = coalesce_columns(
        df,
        "PRODUCT_NAME",
        [
            "PRODUCT_NAME",
            "PROD_NAME",
            "PRD_NAME",
            "PRODUCT_NM",
            "PRDNAME",
            "PRODUCTNAME",
            "PRODUCT_NAME_X",
            "PRODUCT_NAME_Y",
            "DESCR",
            "DESCRIPTION",
            "NOMBRE",
            "PRODUCT_NAME_PROD",
            "PRODUCT_NAME_SALES",
        ],
        default=DEFAULT_TEXT,
    )
    df = coalesce_columns(df, "BRAND", ["BRAND", "MARCA", "LINEA", "FABRICANTE"], default=DEFAULT_TEXT)
    df = coalesce_columns(df, "CATEGORY", ["CATEGORY", "CATEGORIA", "CAT", "DEPTO", "DEPARTAMENTO"])
    df = coalesce_columns(df, "STOCK_QTY", ["STOCK_QTY", "EXISTENCIA", "STOCK"], default=0)
    df = coalesce_columns(df, "COST_MXN", ["COST_MXN", "COSTO", "COSTO_MXN"], default=0)
    df = coalesce_columns(df, "PRICE_MXN", ["PRICE_MXN", "PRECIO", "PRECIO_MXN"], default=0)
    df = coalesce_columns(df, "MIN_STOCK", ["MIN_STOCK", "MIN_STK", "MINIMO", "MIN_INV"])
    df = coalesce_columns(df, "MAX_STOCK", ["MAX_STOCK", "MAX_STK", "MAXIMO", "MAX_INV"])
    if "MIN_STOCK" in df.columns:
        df["MIN_STOCK"] = pd.to_numeric(df["MIN_STOCK"], errors="coerce").fillna(0)
    if "MAX_STOCK" in df.columns:
        df["MAX_STOCK"] = pd.to_numeric(df["MAX_STOCK"], errors="coerce").fillna(0)
    return df


def canonicalize_sales(df_sales: pd.DataFrame) -> pd.DataFrame:
    df = normalize_columns(df_sales)
    df = coalesce_columns(df, "SALE_DATE", ["SALE_DATE", "DATE", "FECHA", "FEC", "FECHA_FACTURA"])
    df = coalesce_columns(df, "FACT_ID", ["FACT_ID", "FACTURA_ID", "SALE_ID"])
    df = coalesce_columns(df, "CLIENT_ID", ["CLIENT_ID", "CLNT_ID", "ID_CLIENTE"])
    df = coalesce_columns(df, "PRODUCT_ID", ["PRODUCT_ID", "PROD_ID", "ID_PRODUCTO"])
    df = coalesce_columns(
        df,
        "PRODUCT_NAME",
        [
            "PRODUCT_NAME",
            "PROD_NAME",
            "PRD_NAME",
            "PRODUCT_NM",
            "PRDNAME",
            "PRODUCTNAME",
            "DESCR",
            "DESCRIPTION",
            "NOMBRE",
        ],
        default=DEFAULT_TEXT,
    )
    df = coalesce_columns(df, "QTY", ["QTY", "QUANTITY", "CANTIDAD", "CANT"], default=0)
    df = coalesce_columns(df, "TOTAL_MXN", ["TOTAL_MXN", "AMOUNT_MXN", "AMT_MXN", "REVENUE_MXN"])
    df = coalesce_columns(df, "TOTAL_USD", ["TOTAL_USD", "AMOUNT_USD", "AMT_USD", "REVENUE_USD"])
    df = coalesce_columns(df, "CURRENCY", ["CURRENCY", "MONEDA"], default="MXN")
    df = coalesce_columns(
        df,
        "FX_RATE",
        ["FX_RATE", "USD_MXN_RATE", "USD_MXN", "TIPO_CAMBIO", "TC"],
    )
    df = coalesce_columns(df, "CHANNEL", ["CHANNEL", "ORIGEN_VENTA", "ORIGEN_VT"])
    df = coalesce_columns(df, "CLIENT_SOURCE", ["CLIENT_SOURCE", "CLIENT_ORIGIN", "RECOMM_SOURCE"])
    df = coalesce_columns(df, "ORDER_TYPE", ["ORDER_TYPE", "TIPO_ORDEN", "TIPO_ORDN"])
    df = coalesce_columns(df, "INVOICE_TYPE", ["INVOICE_TYPE", "TIPO_FACTURA", "TIPO_FACT"])
    df = coalesce_columns(df, "STATUS", ["STATUS", "ESTATUS"])
    return df


def ensure_inventory_columns(
    df_inventory: pd.DataFrame,
    period_days: int | None = None,
    sales_units: pd.DataFrame | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    warnings: list[str] = []
    df = df_inventory.copy()
    original_columns = set(df.columns)

    defaults = {
        "PRODUCT_NAME": DEFAULT_TEXT,
        "BRAND": DEFAULT_TEXT,
        "CATEGORY": DEFAULT_TEXT,
        "STOCK_QTY": 0,
        "MIN_STOCK": pd.NA,
        "MAX_STOCK": pd.NA,
        "COST_MXN": pd.NA,
        "PRICE_MXN": pd.NA,
    }
    for column, default in defaults.items():
        if column not in df.columns:
            df[column] = default

    for column in ["STOCK_QTY", "MIN_STOCK", "MAX_STOCK", "COST_MXN", "PRICE_MXN"]:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df["STOCK_QTY"] = df["STOCK_QTY"].fillna(0)

    if df["MIN_STOCK"].isna().all():
        df["MIN_STOCK"] = df["STOCK_QTY"] * 0.2
    df["MIN_STOCK"] = df["MIN_STOCK"].fillna(df["STOCK_QTY"] * 0.2)
    if df["MAX_STOCK"].isna().all():
        df["MAX_STOCK"] = df["STOCK_QTY"] * 1.6
    df["MAX_STOCK"] = df["MAX_STOCK"].fillna(df["STOCK_QTY"] * 1.6)

    if "units" not in df.columns:
        df["units"] = pd.NA
    unit_candidates = ["units", "QTY", "UNITS", "CANTIDAD", "PIEZAS", "UNITS_SOLD", "SOLD_UNITS"]
    for candidate in unit_candidates:
        if candidate in df.columns:
            df["units"] = df["units"].where(df["units"].notna(), df[candidate])
    df["units"] = pd.to_numeric(df["units"], errors="coerce").fillna(0)

    if sales_units is not None and not sales_units.empty and "PRODUCT_ID" in df.columns:
        if "units" in sales_units.columns and "PRODUCT_ID" in sales_units.columns:
            sales_units = sales_units.copy()
            sales_units["units"] = pd.to_numeric(sales_units["units"], errors="coerce").fillna(0)
            df = df.merge(sales_units[["PRODUCT_ID", "units"]], on="PRODUCT_ID", how="left", suffixes=("", "_SALES"))
            df["units"] = df["units"].where(df["units"].ne(0), df["units_SALES"].fillna(0))
            df = df.drop(columns=["units_SALES"])

    if "revenue" not in df.columns:
        df["revenue"] = pd.NA
    df["revenue"] = df["revenue"].where(df["revenue"].notna(), df["units"] * df["PRICE_MXN"].fillna(0))
    df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce").fillna(0)

    if "inventory_value" not in df.columns:
        df["inventory_value"] = pd.NA

    cost_available = "COST_MXN" in original_columns
    price_available = "PRICE_MXN" in original_columns
    if not cost_available and not price_available:
        warnings.append(
            "No se encontraron COST_MXN ni PRICE_MXN; el valor de inventario se mostrará en 0."
        )

    if cost_available:
        base_cost = df["COST_MXN"].fillna(0)
    elif price_available:
        base_cost = df["PRICE_MXN"].fillna(0)
    else:
        base_cost = 0
    df["inventory_value"] = df["inventory_value"].where(
        df["inventory_value"].notna(), df["STOCK_QTY"].fillna(0) * base_cost
    )
    df["inventory_value"] = pd.to_numeric(df["inventory_value"], errors="coerce").fillna(0)

    if "DAYS_INVENTORY" not in df.columns:
        df["DAYS_INVENTORY"] = pd.NA

    if "avg_daily_units" in df.columns:
        avg_daily = pd.to_numeric(df["avg_daily_units"], errors="coerce").fillna(0)
    elif period_days and period_days > 0:
        avg_daily = df["units"] / float(period_days)
    else:
        avg_daily = pd.Series(0, index=df.index)

    df["DAYS_INVENTORY"] = df["DAYS_INVENTORY"].where(
        df["DAYS_INVENTORY"].notna(),
        df["STOCK_QTY"].div(avg_daily.replace(0, pd.NA)),
    )
    df["DAYS_INVENTORY"] = pd.to_numeric(df["DAYS_INVENTORY"], errors="coerce").fillna(0)

    return df, warnings
