from __future__ import annotations

import re
from typing import Iterable

import pandas as pd


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    normalized = []
    for column in df.columns:
        cleaned = re.sub(r"[^0-9A-Za-z_]+", "_", str(column).strip().upper())
        cleaned = re.sub(r"_+", "_", cleaned).strip("_")
        normalized.append(cleaned)
    df.columns = normalized
    return df


def coalesce_column(
    df: pd.DataFrame,
    target: str,
    candidates: Iterable[str],
    drop_candidates: bool = True,
) -> pd.DataFrame:
    df = df.copy()
    if target not in df.columns:
        df[target] = pd.NA
    for candidate in candidates:
        if candidate in df.columns:
            df[target] = df[target].combine_first(df[candidate])
    if drop_candidates:
        for candidate in candidates:
            if candidate != target and candidate in df.columns:
                df = df.drop(columns=candidate)
    return df


def ensure_columns(df: pd.DataFrame, required: Iterable[str], context: str) -> None:
    missing = sorted(set(required) - set(df.columns))
    if missing:
        available = ", ".join(sorted(df.columns))
        raise ValueError(
            f"Faltan columnas requeridas en {context}: {', '.join(missing)}. "
            f"Disponibles: {available}"
        )


def canonicalize_products(df_products: pd.DataFrame) -> pd.DataFrame:
    df = normalize_columns(df_products)
    df = coalesce_column(df, "SKU", ["SKU", "CODIGO", "COD_PRODUCTO"], drop_candidates=False)
    df = coalesce_column(
        df,
        "PRODUCT_NAME",
        ["PRODUCT_NAME", "PRODUCT_NAME_X", "PRODUCT_NAME_Y", "PRODUCT_NAME_PROD", "PRODUCT_NAME_SALES"],
    )
    df = coalesce_column(df, "STOCK_QTY", ["STOCK_QTY", "EXISTENCIA"], drop_candidates=False)
    df = coalesce_column(df, "COST_MXN", ["COST_MXN", "COSTO", "COSTO_MXN"], drop_candidates=False)
    df = coalesce_column(df, "PRICE_MXN", ["PRICE_MXN", "PRECIO", "PRECIO_MXN"], drop_candidates=False)
    df = coalesce_column(df, "MIN_STOCK", ["MIN_STOCK", "MINIMO", "MIN_INV"], drop_candidates=False)
    df = coalesce_column(df, "MAX_STOCK", ["MAX_STOCK", "MAXIMO", "MAX_INV"], drop_candidates=False)
    required = {
        "PRODUCT_ID",
        "SKU",
        "PRODUCT_NAME",
        "BRAND",
        "CATEGORY",
        "STOCK_QTY",
        "COST_MXN",
        "PRICE_MXN",
        "MIN_STOCK",
        "MAX_STOCK",
    }
    ensure_columns(df, required, "productos")
    return df


def canonicalize_sales(df_sales: pd.DataFrame) -> pd.DataFrame:
    df = normalize_columns(df_sales)
    df = coalesce_column(df, "DATE", ["DATE", "SALE_DATE", "FECHA"], drop_candidates=False)
    df = coalesce_column(df, "FACT_ID", ["FACT_ID", "FACTURA_ID", "SALE_ID"], drop_candidates=False)
    df = coalesce_column(df, "CLIENT_ID", ["CLIENT_ID"], drop_candidates=False)
    df = coalesce_column(df, "PRODUCT_ID", ["PRODUCT_ID"], drop_candidates=False)
    df = coalesce_column(df, "QTY", ["QTY", "QUANTITY", "CANTIDAD"], drop_candidates=False)
    df = coalesce_column(df, "TOTAL_MXN", ["TOTAL_MXN", "REVENUE_MXN", "AMOUNT_MXN"], drop_candidates=False)
    df = coalesce_column(df, "CURRENCY", ["CURRENCY", "MONEDA"], drop_candidates=False)
    df = coalesce_column(df, "FX_RATE", ["FX_RATE", "USD_MXN_RATE", "TIPO_CAMBIO"], drop_candidates=False)
    df = coalesce_column(df, "CHANNEL", ["CHANNEL", "ORIGEN_VENTA"], drop_candidates=False)
    df = coalesce_column(
        df,
        "CLIENT_SOURCE",
        ["CLIENT_SOURCE", "CLIENT_ORIGIN", "RECOMM_SOURCE"],
        drop_candidates=False,
    )
    df = coalesce_column(df, "ORDER_TYPE", ["ORDER_TYPE", "TIPO_ORDEN"], drop_candidates=False)
    df = coalesce_column(df, "INVOICE_TYPE", ["INVOICE_TYPE", "TIPO_FACTURA"], drop_candidates=False)
    df = coalesce_column(df, "STATUS", ["STATUS"], drop_candidates=False)
    required = {
        "DATE",
        "FACT_ID",
        "CLIENT_ID",
        "PRODUCT_ID",
        "QTY",
        "TOTAL_MXN",
        "CURRENCY",
        "FX_RATE",
        "CHANNEL",
        "CLIENT_SOURCE",
        "ORDER_TYPE",
        "INVOICE_TYPE",
        "STATUS",
    }
    ensure_columns(df, required, "ventas")
    return df
