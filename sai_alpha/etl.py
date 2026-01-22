from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from dbfread import DBF


@dataclass
class DataBundle:
    ventas: pd.DataFrame
    productos: pd.DataFrame
    clientes: pd.DataFrame
    vendedores: pd.DataFrame
    tipo_cambio: pd.DataFrame | None = None
    facturas: pd.DataFrame | None = None
    notas_credito: pd.DataFrame | None = None
    pedidos: pd.DataFrame | None = None


def _read_dbf_to_df(path: Path) -> pd.DataFrame:
    table = DBF(path, load=True, char_decode_errors="ignore")
    df = pd.DataFrame(iter(table))
    for col in ("SALE_DATE", "ORDER_DATE", "FECHA", "DATE"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col])
    return df


def resolve_dbf_dir(default_dir: Path | None = None) -> Path:
    env_value = os.getenv("SAI_ALPHA_DBF_DIR")
    if env_value:
        return Path(env_value)
    if default_dir is None:
        default_dir = Path("data") / "dbf"
    return default_dir


def _normalize_columns(df: pd.DataFrame, aliases: dict[str, list[str]]) -> pd.DataFrame:
    rename_map: dict[str, str] = {}
    for canonical, candidates in aliases.items():
        for candidate in candidates:
            if candidate in df.columns:
                rename_map[candidate] = canonical
                break
    if rename_map:
        df = df.rename(columns=rename_map)
    return df


def load_data(dbf_dir: Path) -> DataBundle:
    ventas = _read_dbf_to_df(dbf_dir / "ventas.dbf")
    productos = _read_dbf_to_df(dbf_dir / "productos.dbf")
    clientes = _read_dbf_to_df(dbf_dir / "clientes.dbf")
    vendedores = _read_dbf_to_df(dbf_dir / "vendedores.dbf")

    ventas = _normalize_columns(
        ventas,
        {
            "SALE_DATE": ["SALE_DATE", "FECHA"],
            "PRODUCT_ID": ["PRODUCT_ID"],
            "PRODUCT_NAME": ["PRODUCT_NAME", "PROD_NAME"],
            "BRAND": ["BRAND"],
            "CATEGORY": ["CATEGORY"],
            "CLIENT_ID": ["CLIENT_ID"],
            "CLIENT_NAME": ["CLIENT_NAME", "CLNT_NAME"],
            "CLIENT_ORIGIN": ["CLIENT_ORIGIN", "ORIGEN_CLI", "CLNT_ORIG"],
            "SELLER_ID": ["SELLER_ID", "VENDOR_ID"],
            "SELLER_NAME": ["SELLER_NAME", "VENDOR_NAME", "VEND_NAME", "SELLER_NM"],
            "ORIGEN_VENTA": ["ORIGEN_VENTA", "ORIGEN_VTA", "ORIGEN_VT"],
            "RECOMM_SOURCE": ["RECOMM_SOURCE", "ENCUESTA", "RECOMENDACION", "RECOM_SRC"],
            "TIPO_FACTURA": ["TIPO_FACTURA", "TIPO_FACT"],
            "TIPO_ORDEN": ["TIPO_ORDEN", "TIPO_ORDN"],
            "STATUS": ["STATUS"],
            "QTY": ["QTY", "QUANTITY"],
            "UNIT_PRICE_MXN": ["UNIT_PRICE_MXN", "UNIT_PRICE", "UNIT_MXN"],
            "AMOUNT_MXN": ["AMOUNT_MXN", "REVENUE", "AMT_MXN"],
            "AMOUNT_USD": ["AMOUNT_USD", "REV_USD", "REVENUE_USD", "AMT_USD"],
            "CURRENCY": ["CURRENCY", "MONEDA"],
            "USD_MXN_RATE": ["USD_MXN_RATE", "TC_MXN_USD", "USD_MXN"],
            "FACTURA_ID": ["FACTURA_ID", "FACT_ID"],
        },
    )
    productos = _normalize_columns(
        productos,
        {
            "PRODUCT_ID": ["PRODUCT_ID"],
            "PRODUCT_NAME": ["PRODUCT_NAME", "PROD_NAME"],
            "BRAND": ["BRAND"],
            "CATEGORY": ["CATEGORY"],
            "COST_MXN": ["COST_MXN", "BASE_COST"],
            "PRICE_MXN": ["PRICE_MXN", "BASE_PRICE"],
            "STOCK_QTY": ["STOCK_QTY", "EXISTENCIA"],
            "MIN_STOCK": ["MIN_STOCK", "MIN_STK"],
            "MAX_STOCK": ["MAX_STOCK", "MAX_STK"],
            "SKU": ["SKU"],
        },
    )
    clientes = _normalize_columns(
        clientes,
        {
            "CLIENT_ID": ["CLIENT_ID"],
            "CLIENT_NAME": ["CLIENT_NAME", "CLNT_NAME"],
            "CLIENT_ORIGIN": ["CLIENT_ORIGIN", "ORIGEN_CLI"],
            "RECOMM_SOURCE": ["RECOMM_SOURCE", "RECOM_SRC"],
            "REGION": ["REGION"],
            "LAST_PURCHASE": ["LAST_PURCHASE", "LAST_PURCH", "LAST_PCH"],
            "CONTACT": ["CONTACT"],
            "STATUS": ["STATUS"],
        },
    )
    vendedores = _normalize_columns(
        vendedores,
        {
            "SELLER_ID": ["SELLER_ID", "VENDOR_ID"],
            "SELLER_NAME": ["SELLER_NAME", "VENDOR_NAME", "VEND_NAME", "SELLER_NM"],
            "REGION": ["REGION"],
            "TEAM": ["TEAM"],
        },
    )

    tipo_cambio_path = dbf_dir / "tipo_cambio.dbf"
    tcambio_path = dbf_dir / "tcambio.dbf"
    facturas_path = dbf_dir / "facturas.dbf"
    notas_path = dbf_dir / "notas_credito.dbf"
    pedidos_path = dbf_dir / "pedidos.dbf"

    tipo_cambio = None
    if tipo_cambio_path.exists():
        tipo_cambio = _read_dbf_to_df(tipo_cambio_path)
        tipo_cambio = _normalize_columns(
            tipo_cambio,
            {"DATE": ["DATE", "FECHA"], "USD_MXN": ["USD_MXN", "TC_MXN_USD"]},
        )
    elif tcambio_path.exists():
        tipo_cambio = _read_dbf_to_df(tcambio_path)
        tipo_cambio = _normalize_columns(tipo_cambio, {"DATE": ["FECHA"], "USD_MXN": ["TC_MXN_USD"]})

    facturas = _read_dbf_to_df(facturas_path) if facturas_path.exists() else None
    if facturas is not None:
        facturas = _normalize_columns(
            facturas,
            {
                "FECHA": ["FECHA", "DATE"],
                "CLIENT_ID": ["CLIENT_ID"],
                "CLIENT_NAME": ["CLIENT_NAME", "CLNT_NAME"],
                "SELLER_ID": ["SELLER_ID", "VENDOR_ID"],
                "SELLER_NAME": ["SELLER_NAME", "VENDOR_NAME", "SELLER_NM"],
                "TIPO_FACTURA": ["TIPO_FACTURA", "TIPO_FACT"],
                "TIPO_ORDEN": ["TIPO_ORDEN", "TIPO_ORDN"],
                "ORIGEN_VENTA": ["ORIGEN_VENTA", "ORIGEN_VTA", "ORIGEN_VT"],
                "RECOMM_SOURCE": ["RECOMM_SOURCE", "RECOM_SRC"],
                "CURRENCY": ["CURRENCY", "MONEDA"],
                "USD_MXN_RATE": ["USD_MXN_RATE", "TC_MXN_USD", "USD_MXN"],
                "SUBTOTAL_MXN": ["SUBTOTAL_MXN", "SUBT_MXN"],
                "TOTAL_MXN": ["TOTAL_MXN", "REVENUE"],
                "FACTURA_ID": ["FACTURA_ID", "FACT_ID"],
            },
        )
    notas_credito = _read_dbf_to_df(notas_path) if notas_path.exists() else None
    if notas_credito is not None:
        notas_credito = _normalize_columns(
            notas_credito,
            {"FECHA": ["FECHA"], "MONTO_MXN": ["MONTO_MXN"], "FACTURA_ID": ["FACTURA_ID", "FACT_ID"]},
        )

    pedidos = _read_dbf_to_df(pedidos_path) if pedidos_path.exists() else None
    if pedidos is not None:
        pedidos = _normalize_columns(
            pedidos,
            {
                "ORDER_DATE": ["ORDER_DATE", "FECHA"],
                "CLIENT_ID": ["CLIENT_ID"],
                "CLIENT_NAME": ["CLIENT_NAME", "CLNT_NAME"],
                "SELLER_ID": ["SELLER_ID", "VENDOR_ID"],
                "SELLER_NAME": ["SELLER_NAME", "VENDOR_NAME", "VEND_NAME", "SELLER_NM"],
                "PRODUCT_ID": ["PRODUCT_ID"],
                "PRODUCT_NAME": ["PRODUCT_NAME", "PROD_NAME"],
                "QTY_ORDER": ["QTY_ORDER"],
                "QTY_PENDING": ["QTY_PENDING", "QTY_PEND"],
                "STATUS": ["STATUS"],
                "ORIGEN_VENTA": ["ORIGEN_VENTA", "ORIGEN_VTA", "ORIGEN_VT"],
                "TIPO_ORDEN": ["TIPO_ORDEN", "TIPO_ORDN"],
            },
        )

    return DataBundle(
        ventas=ventas,
        productos=productos,
        clientes=clientes,
        vendedores=vendedores,
        tipo_cambio=tipo_cambio,
        facturas=facturas,
        notas_credito=notas_credito,
        pedidos=pedidos,
    )


def enrich_sales(bundle: DataBundle) -> pd.DataFrame:
    ventas = bundle.ventas.copy()
    if bundle.tipo_cambio is not None and "USD_MXN_RATE" not in ventas.columns:
        tipo_cambio = bundle.tipo_cambio.copy()
        tipo_cambio = tipo_cambio.rename(columns={"DATE": "SALE_DATE", "USD_MXN": "USD_MXN_RATE"})
        ventas = ventas.merge(tipo_cambio, on="SALE_DATE", how="left")

    ventas = ventas.merge(bundle.productos, on="PRODUCT_ID", how="left", suffixes=("", "_PROD"))
    ventas = ventas.merge(bundle.clientes, on="CLIENT_ID", how="left", suffixes=("", "_CLI"))
    ventas = ventas.merge(bundle.vendedores, on="SELLER_ID", how="left", suffixes=("", "_SELL"))

    if "PRODUCT_NAME" not in ventas.columns or ventas["PRODUCT_NAME"].isna().any():
        if "PRODUCT_NAME_PROD" in ventas.columns:
            ventas["PRODUCT_NAME"] = ventas["PRODUCT_NAME"].fillna(ventas["PRODUCT_NAME_PROD"])
    if "BRAND" not in ventas.columns or ventas["BRAND"].isna().any():
        if "BRAND_PROD" in ventas.columns:
            ventas["BRAND"] = ventas["BRAND"].fillna(ventas["BRAND_PROD"])
    if "CATEGORY" not in ventas.columns or ventas["CATEGORY"].isna().any():
        if "CATEGORY_PROD" in ventas.columns:
            ventas["CATEGORY"] = ventas["CATEGORY"].fillna(ventas["CATEGORY_PROD"])
    if "CLIENT_NAME" not in ventas.columns or ventas["CLIENT_NAME"].isna().any():
        if "CLIENT_NAME_CLI" in ventas.columns:
            ventas["CLIENT_NAME"] = ventas["CLIENT_NAME"].fillna(ventas["CLIENT_NAME_CLI"])
    if "CLIENT_ORIGIN" not in ventas.columns or ventas["CLIENT_ORIGIN"].isna().any():
        if "CLIENT_ORIGIN_CLI" in ventas.columns:
            ventas["CLIENT_ORIGIN"] = ventas["CLIENT_ORIGIN"].fillna(ventas["CLIENT_ORIGIN_CLI"])
    if "RECOMM_SOURCE" not in ventas.columns or ventas["RECOMM_SOURCE"].isna().any():
        if "RECOMM_SOURCE_CLI" in ventas.columns:
            ventas["RECOMM_SOURCE"] = ventas["RECOMM_SOURCE"].fillna(ventas["RECOMM_SOURCE_CLI"])
    if "SELLER_NAME" not in ventas.columns or ventas["SELLER_NAME"].isna().any():
        if "SELLER_NAME_SELL" in ventas.columns:
            ventas["SELLER_NAME"] = ventas["SELLER_NAME"].fillna(ventas["SELLER_NAME_SELL"])
    if "ORIGEN_VENTA" in ventas.columns:
        ventas["ORIGEN_VENTA"] = ventas["ORIGEN_VENTA"].fillna("Mostrador")
    if "CLIENT_ORIGIN" in ventas.columns:
        ventas["CLIENT_ORIGIN"] = ventas["CLIENT_ORIGIN"].fillna("Walk-in")
    if "RECOMM_SOURCE" in ventas.columns:
        ventas["RECOMM_SOURCE"] = ventas["RECOMM_SOURCE"].fillna("Sin encuesta")

    if "USD_MXN_RATE" in ventas.columns:
        ventas["USD_MXN_RATE"] = ventas["USD_MXN_RATE"].astype(float)

    if "AMOUNT_MXN" in ventas.columns:
        ventas["REVENUE_MXN"] = ventas["AMOUNT_MXN"].astype(float)
    elif "AMOUNT_USD" in ventas.columns and "USD_MXN_RATE" in ventas.columns:
        ventas["REVENUE_MXN"] = ventas["AMOUNT_USD"].astype(float) * ventas["USD_MXN_RATE"]

    if "AMOUNT_USD" in ventas.columns:
        ventas["REVENUE_USD"] = ventas["AMOUNT_USD"].astype(float)
    elif "REVENUE_MXN" in ventas.columns and "USD_MXN_RATE" in ventas.columns:
        ventas["REVENUE_USD"] = ventas["REVENUE_MXN"] / ventas["USD_MXN_RATE"].replace(0, pd.NA)

    if "UNIT_PRICE_MXN" in ventas.columns:
        ventas["UNIT_PRICE_MXN"] = ventas["UNIT_PRICE_MXN"].astype(float)
    elif "UNIT_PRICE" in ventas.columns:
        ventas["UNIT_PRICE_MXN"] = ventas["UNIT_PRICE"].astype(float)

    if "UNIT_PRICE_MXN" in ventas.columns and "USD_MXN_RATE" in ventas.columns:
        ventas["UNIT_PRICE_USD"] = ventas["UNIT_PRICE_MXN"] / ventas["USD_MXN_RATE"].replace(0, pd.NA)
    else:
        ventas["UNIT_PRICE_USD"] = ventas.get("UNIT_PRICE_MXN", pd.Series(dtype=float))

    if "QTY" in ventas.columns:
        ventas["QTY"] = ventas["QTY"].astype(int)
    elif "QUANTITY" in ventas.columns:
        ventas["QTY"] = ventas["QUANTITY"].astype(int)
    return ventas


def enrich_pedidos(bundle: DataBundle) -> pd.DataFrame:
    if bundle.pedidos is None:
        return pd.DataFrame()
    pedidos = bundle.pedidos.copy()
    pedidos = pedidos.merge(bundle.productos, on="PRODUCT_ID", how="left", suffixes=("", "_PROD"))
    pedidos = pedidos.merge(bundle.clientes, on="CLIENT_ID", how="left", suffixes=("", "_CLI"))
    pedidos = pedidos.merge(bundle.vendedores, on="SELLER_ID", how="left", suffixes=("", "_SELL"))
    return pedidos


def filter_sales(
    ventas: pd.DataFrame,
    date_range: tuple[pd.Timestamp, pd.Timestamp] | None,
    brands: list[str],
    vendors: list[str],
) -> pd.DataFrame:
    df = ventas.copy()
    if date_range:
        start, end = date_range
        df = df[(df["SALE_DATE"] >= start) & (df["SALE_DATE"] <= end)]
    if brands:
        df = df[df["BRAND"].isin(brands)]
    if vendors:
        df = df[df["SELLER_NAME"].isin(vendors)]
    return df
