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
            df[target] = df[target].combine_first(df[candidate])
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
