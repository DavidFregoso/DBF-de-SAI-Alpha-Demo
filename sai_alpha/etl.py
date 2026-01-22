from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from dbfread import DBF
import streamlit as st


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


COMMON_ALIASES: dict[str, list[str]] = {
    "PRODUCT_ID": ["PRODUCT_ID", "PROD_ID", "PRODUCTO_ID", "ID_PRODUCTO", "ID_PROD", "IDARTIC", "ID_ARTIC"],
    "PRODUCT_NAME": [
        "PRODUCT_NAME",
        "PROD_NAME",
        "NOMBRE",
        "NOMPROD",
        "PRODUCTO",
        "DESCRIP",
        "DESCRIPCION",
        "DESC",
        "ARTICULO",
        "ITEM_NAME",
    ],
    "BRAND": ["BRAND", "MARCA", "BRANDS"],
    "CATEGORY": ["CATEGORY", "CATEGORIA", "CAT"],
    "EXISTENCIA": ["EXISTENCIA", "STOCK", "EXIST", "ON_HAND", "INV", "INVENTARIO"],
    "DATE": ["DATE", "FECHA", "FEC", "EMISION", "FACT_DATE"],
    "AMOUNT_MXN": ["AMOUNT_MXN", "REVENUE", "AMT_MXN", "TOTAL_MXN", "MONTO_MXN", "IMPORTE_MXN"],
    "AMOUNT_USD": ["AMOUNT_USD", "REV_USD", "REVENUE_USD", "AMT_USD", "TOTAL_USD", "MONTO_USD", "IMPORTE_USD"],
    "SELLER_ID": ["SELLER_ID", "VENDOR_ID", "VENDEDOR", "ID_VENDEDOR"],
    "SELLER_NAME": ["SELLER_NAME", "VENDOR_NAME", "VEND_NAME", "SELLER_NM", "NOMBRE_VENDEDOR"],
}

TABLE_ALIASES: dict[str, dict[str, list[str]]] = {
    "ventas": {
        "SALE_DATE": ["SALE_DATE", "DATE", "FECHA", "FEC", "EMISION", "FACT_DATE"],
        "CLIENT_ID": ["CLIENT_ID", "CLNT_ID", "ID_CLIENTE"],
        "CLIENT_NAME": ["CLIENT_NAME", "CLNT_NAME", "CLIENTE", "NOMBRE_CLI"],
        "CLIENT_ORIGIN": ["CLIENT_ORIGIN", "ORIGEN_CLI", "CLNT_ORIG", "ORIGEN_CLIENTE"],
        "ORIGEN_VENTA": ["ORIGEN_VENTA", "ORIGEN_VTA", "ORIGEN_VT"],
        "RECOMM_SOURCE": ["RECOMM_SOURCE", "ENCUESTA", "RECOMENDACION", "RECOM_SRC"],
        "TIPO_FACTURA": ["TIPO_FACTURA", "TIPO_FACT"],
        "TIPO_ORDEN": ["TIPO_ORDEN", "TIPO_ORDN"],
        "STATUS": ["STATUS", "ESTATUS"],
        "QTY": ["QTY", "QUANTITY", "CANTIDAD", "CANT"],
        "UNIT_PRICE_MXN": ["UNIT_PRICE_MXN", "UNIT_PRICE", "UNIT_MXN", "PRECIO_UNIT", "PRECIO"],
        "CURRENCY": ["CURRENCY", "MONEDA"],
        "USD_MXN_RATE": ["USD_MXN_RATE", "TC_MXN_USD", "USD_MXN", "TIPO_CAMBIO"],
        "FACTURA_ID": ["FACTURA_ID", "FACT_ID", "ID_FACTURA"],
        "SALE_ID": ["SALE_ID", "VENTA_ID", "ID_VENTA"],
    },
    "productos": {
        "COST_MXN": ["COST_MXN", "BASE_COST", "COSTO", "COSTO_MXN"],
        "PRICE_MXN": ["PRICE_MXN", "BASE_PRICE", "PRECIO", "PRECIO_MXN"],
        "STOCK_QTY": ["STOCK_QTY", "EXISTENCIA", "STOCK", "INV", "INVENTARIO", "EXIST", "ON_HAND"],
        "MIN_STOCK": ["MIN_STOCK", "MIN_STK", "MINIMO", "MIN_INV"],
        "MAX_STOCK": ["MAX_STOCK", "MAX_STK", "MAXIMO", "MAX_INV"],
        "SKU": ["SKU", "CODIGO", "COD_PRODUCTO"],
    },
    "clientes": {
        "CLIENT_ID": ["CLIENT_ID", "CLNT_ID", "ID_CLIENTE"],
        "CLIENT_NAME": ["CLIENT_NAME", "CLNT_NAME", "CLIENTE", "NOMBRE_CLI"],
        "CLIENT_ORIGIN": ["CLIENT_ORIGIN", "ORIGEN_CLI", "ORIGEN_CLIENTE"],
        "RECOMM_SOURCE": ["RECOMM_SOURCE", "RECOM_SRC", "ENCUESTA", "RECOMENDACION"],
        "REGION": ["REGION", "ZONA"],
        "LAST_PURCHASE": ["LAST_PURCHASE", "LAST_PURCH", "LAST_PCH", "ULT_COMPRA"],
        "CONTACT": ["CONTACT", "CONTACTO"],
        "STATUS": ["STATUS", "ESTATUS"],
    },
    "vendedores": {
        "REGION": ["REGION", "ZONA"],
        "TEAM": ["TEAM", "EQUIPO"],
    },
    "tipo_cambio": {
        "DATE": ["DATE", "FECHA", "FEC", "EMISION", "FACT_DATE"],
        "USD_MXN": ["USD_MXN", "TC_MXN_USD", "TIPO_CAMBIO"],
    },
    "tcambio": {
        "DATE": ["DATE", "FECHA", "FEC", "EMISION", "FACT_DATE"],
        "USD_MXN": ["USD_MXN", "TC_MXN_USD", "TIPO_CAMBIO"],
    },
    "facturas": {
        "DATE": ["DATE", "FECHA", "FEC", "EMISION", "FACT_DATE"],
        "CLIENT_ID": ["CLIENT_ID", "CLNT_ID", "ID_CLIENTE"],
        "CLIENT_NAME": ["CLIENT_NAME", "CLNT_NAME", "CLIENTE", "NOMBRE_CLI"],
        "TIPO_FACTURA": ["TIPO_FACTURA", "TIPO_FACT"],
        "TIPO_ORDEN": ["TIPO_ORDEN", "TIPO_ORDN"],
        "ORIGEN_VENTA": ["ORIGEN_VENTA", "ORIGEN_VTA", "ORIGEN_VT"],
        "RECOMM_SOURCE": ["RECOMM_SOURCE", "RECOM_SRC", "ENCUESTA", "RECOMENDACION"],
        "CURRENCY": ["CURRENCY", "MONEDA"],
        "USD_MXN_RATE": ["USD_MXN_RATE", "TC_MXN_USD", "USD_MXN", "TIPO_CAMBIO"],
        "SUBTOTAL_MXN": ["SUBTOTAL_MXN", "SUBT_MXN", "SUBTOTAL", "SUBTOTAL_MX"],
        "TOTAL_MXN": ["TOTAL_MXN", "REVENUE", "TOTAL", "TOTAL_MX", "MONTO_MXN"],
        "FACTURA_ID": ["FACTURA_ID", "FACT_ID", "ID_FACTURA"],
    },
    "notas_credito": {
        "DATE": ["DATE", "FECHA", "FEC"],
        "MONTO_MXN": ["MONTO_MXN", "AMOUNT_MXN", "IMPORTE_MXN"],
        "FACTURA_ID": ["FACTURA_ID", "FACT_ID", "ID_FACTURA"],
        "CLIENT_ID": ["CLIENT_ID", "CLNT_ID", "ID_CLIENTE"],
    },
    "pedidos": {
        "ORDER_DATE": ["ORDER_DATE", "DATE", "FECHA", "FEC", "EMISION", "FACT_DATE"],
        "CLIENT_ID": ["CLIENT_ID", "CLNT_ID", "ID_CLIENTE"],
        "CLIENT_NAME": ["CLIENT_NAME", "CLNT_NAME", "CLIENTE", "NOMBRE_CLI"],
        "ORIGEN_VENTA": ["ORIGEN_VENTA", "ORIGEN_VTA", "ORIGEN_VT"],
        "TIPO_ORDEN": ["TIPO_ORDEN", "TIPO_ORDN"],
        "STATUS": ["STATUS", "ESTATUS"],
        "QTY_ORDER": ["QTY_ORDER", "QTY", "QUANTITY", "CANTIDAD", "CANT"],
        "QTY_PENDING": ["QTY_PENDING", "QTY_PEND", "PENDIENTE", "PEND"],
        "PRICE_MXN": ["PRICE_MXN", "PRECIO", "PRECIO_MXN", "UNIT_PRICE", "UNIT_PRICE_MXN"],
        "ORDER_ID": ["ORDER_ID", "PEDIDO_ID", "ID_PEDIDO"],
    },
}

PRODUCT_NAME_REQUIRED = {"ventas", "productos", "pedidos"}

STRING_COLUMNS = {"PRODUCT_ID", "PRODUCT_NAME", "BRAND", "CATEGORY", "SELLER_ID", "SELLER_NAME", "VENDOR_ID"}
NUMERIC_COLUMNS = {"EXISTENCIA", "AMOUNT_MXN", "AMOUNT_USD", "STOCK_QTY"}
DATE_COLUMNS = {"SALE_DATE", "ORDER_DATE", "DATE"}


def _standardize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    normalized = []
    for column in df.columns:
        cleaned = str(column).strip().upper().replace("-", "_").replace(" ", "_")
        while "__" in cleaned:
            cleaned = cleaned.replace("__", "_")
        normalized.append(cleaned)
    df.columns = normalized
    return df


def _apply_aliases(df: pd.DataFrame, aliases: dict[str, list[str]]) -> pd.DataFrame:
    rename_map: dict[str, str] = {}
    for canonical, candidates in aliases.items():
        for candidate in candidates:
            if candidate in df.columns:
                rename_map[candidate] = canonical
                break
    if rename_map:
        df = df.rename(columns=rename_map)
    return df


def normalize_columns(df: pd.DataFrame, table_name: str, source_path: Path) -> pd.DataFrame:
    normalized = _standardize_column_names(df)
    table_aliases = TABLE_ALIASES.get(table_name.lower(), {})
    normalized = _apply_aliases(normalized, table_aliases)
    normalized = _apply_aliases(normalized, COMMON_ALIASES)

    for col in DATE_COLUMNS:
        if col in normalized.columns:
            normalized[col] = pd.to_datetime(normalized[col])

    for col in STRING_COLUMNS:
        if col in normalized.columns:
            normalized[col] = normalized[col].astype("string")

    for col in NUMERIC_COLUMNS:
        if col in normalized.columns:
            normalized[col] = pd.to_numeric(normalized[col], errors="coerce")

    if "STOCK_QTY" in normalized.columns and "EXISTENCIA" not in normalized.columns:
        normalized["EXISTENCIA"] = normalized["STOCK_QTY"]
    if "EXISTENCIA" in normalized.columns and "STOCK_QTY" not in normalized.columns:
        normalized["STOCK_QTY"] = normalized["EXISTENCIA"]
    if "SELLER_ID" in normalized.columns and "VENDOR_ID" not in normalized.columns:
        normalized["VENDOR_ID"] = normalized["SELLER_ID"]

    if table_name.lower() in PRODUCT_NAME_REQUIRED and "PRODUCT_NAME" not in normalized.columns:
        available = ", ".join(normalized.columns)
        message = (
            "No se encontró la columna PRODUCT_NAME después de normalizar. "
            f"DBF cargado: {source_path}. Columnas disponibles: {available}"
        )
        st.error(message)
        st.stop()

    return normalized


def _read_dbf_to_df(path: Path) -> pd.DataFrame:
    table = DBF(path, load=True, char_decode_errors="ignore")
    df = pd.DataFrame(iter(table))
    return normalize_columns(df, path.stem, path)


def resolve_dbf_dir(default_dir: Path | None = None) -> Path:
    env_value = os.getenv("SAI_ALPHA_DBF_DIR")
    if env_value:
        return Path(env_value)
    if default_dir is None:
        default_dir = Path("data") / "dbf"
    return default_dir


def load_data(dbf_dir: Path) -> DataBundle:
    ventas = _read_dbf_to_df(dbf_dir / "ventas.dbf")
    productos = _read_dbf_to_df(dbf_dir / "productos.dbf")
    clientes = _read_dbf_to_df(dbf_dir / "clientes.dbf")
    vendedores = _read_dbf_to_df(dbf_dir / "vendedores.dbf")

    tipo_cambio_path = dbf_dir / "tipo_cambio.dbf"
    tcambio_path = dbf_dir / "tcambio.dbf"
    facturas_path = dbf_dir / "facturas.dbf"
    notas_path = dbf_dir / "notas_credito.dbf"
    pedidos_path = dbf_dir / "pedidos.dbf"

    tipo_cambio = None
    if tipo_cambio_path.exists():
        tipo_cambio = _read_dbf_to_df(tipo_cambio_path)
    elif tcambio_path.exists():
        tipo_cambio = _read_dbf_to_df(tcambio_path)

    facturas = _read_dbf_to_df(facturas_path) if facturas_path.exists() else None
    notas_credito = _read_dbf_to_df(notas_path) if notas_path.exists() else None

    pedidos = _read_dbf_to_df(pedidos_path) if pedidos_path.exists() else None

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
