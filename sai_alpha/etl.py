from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from dbfread import DBF
import numpy as np

from sai_alpha import normalize as normalize_utils
from sai_alpha.schema import DEFAULT_TEXT, coalesce_columns


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
    "PRODUCT_ID": [
        "PRODUCT_ID",
        "PROD_ID",
        "PRODID",
        "PRODUCTO_ID",
        "ID_PRODUCTO",
        "ID_PROD",
        "IDARTIC",
        "ID_ARTIC",
    ],
    "PRODUCT_NAME": [
        "PRODUCT_NAME",
        "PROD_NAME",
        "PRD_NAME",
        "PRODUCT_NM",
        "PRDNAME",
        "PRODUCTNAME",
        "NOMBRE",
        "NOMPROD",
        "PRODUCTO",
        "DESCRIP",
        "DESCRIPCION",
        "DESC",
        "ARTICULO",
        "ITEM_NAME",
        "ITEM",
        "NOM_ART",
    ],
    "BRAND": ["BRAND", "MARCA", "BRANDS", "LINEA", "FABRICANTE"],
    "CATEGORY": ["CATEGORY", "CATEGORIA", "CAT", "DEPTO", "DEPARTAMENTO"],
    "STOCK_QTY": [
        "STOCK_QTY",
        "EXISTENCIA",
        "STOCK",
        "EXIST",
        "ON_HAND",
        "INVENTARIO",
        "CANTIDAD_EXIST",
        "QTY_ON_HAND",
    ],
    "DAYS_INVENTORY": [
        "DAYS_INVENTORY",
        "DIAS_INVENTARIO",
        "DAYS_STOCK",
        "DAYS_ON_HAND",
        "DAYS_INV",
    ],
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
        "CLIENT_ORIGIN": [
            "CLIENT_ORIGIN",
            "ORIGEN_CLI",
            "CLNT_ORIG",
            "ORIGEN_CLIENTE",
            "CLIENT_SOURCE",
            "INV_SOURCE",
        ],
        "ORIGEN_VENTA": ["ORIGEN_VENTA", "ORIGEN_VTA", "ORIGEN_VT", "SALE_ORIG"],
        "RECOMM_SOURCE": ["RECOMM_SOURCE", "ENCUESTA", "RECOMENDACION", "RECOM_SRC"],
        "TIPO_FACTURA": ["TIPO_FACTURA", "TIPO_FACT", "INV_TYPE", "INVOICE_TYPE"],
        "TIPO_ORDEN": ["TIPO_ORDEN", "TIPO_ORDN", "ORD_TYPE", "ORDER_TYPE"],
        "STATUS": ["STATUS", "ESTATUS"],
        "QTY": ["QTY", "QUANTITY", "CANTIDAD", "CANT"],
        "UNIT_PRICE_MXN": ["UNIT_PRICE_MXN", "UNIT_PRICE", "UNIT_MXN", "PRECIO_UNIT", "PRECIO"],
        "CURRENCY": ["CURRENCY", "MONEDA"],
        "USD_MXN_RATE": [
            "USD_MXN_RATE",
            "TC_MXN_USD",
            "USD_MXN",
            "TIPO_CAMBIO",
            "EXCH_RATE",
            "EXCHANGE_RATE",
        ],
        "FACTURA_ID": ["FACTURA_ID", "FACT_ID", "ID_FACTURA"],
        "SALE_ID": ["SALE_ID", "VENTA_ID", "ID_VENTA"],
        "PRODUCT_NAME": ["PRODUCT_NAME", "PROD_NAME", "PRD_NAME", "PRODUCT_NM", "PRDNAME", "PRODUCTNAME"],
        "PRICE_MXN": [
            "PRICE_MXN",
            "PRICE",
            "PRC_MXN",
            "PR_MXN",
            "P_MXN",
            "PRICE_MN",
            "PRECIO",
            "PREC_MXN",
        ],
        "PRICE_USD": ["PRICE_USD", "PRECIO_USD", "PRICE_DLLS", "PRICE_US"],
    },
    "productos": {
        "PRODUCT_ID": ["PRODUCT_ID", "PROD_ID", "PRODID"],
        "PRODUCT_NAME": ["PRODUCT_NAME", "PROD_NAME", "PRD_NAME", "PRODUCT_NM", "PRDNAME", "PRODUCTNAME"],
        "COST_MXN": ["COST_MXN", "BASE_COST", "COSTO", "COSTO_MXN", "COST", "CST_MXN"],
        "PRICE_MXN": [
            "PRICE_MXN",
            "BASE_PRICE",
            "PRICE",
            "PRC_MXN",
            "PR_MXN",
            "P_MXN",
            "PRICE_MN",
            "PRECIO",
            "PRECIO_MXN",
            "PREC_MXN",
        ],
        "STOCK_QTY": ["STOCK_QTY", "EXISTENCIA", "STOCK", "INV", "INVENTARIO", "EXIST", "ON_HAND"],
        "MIN_STOCK": ["MIN_STOCK", "MIN_STK", "MINIMO", "MIN_INV"],
        "MAX_STOCK": ["MAX_STOCK", "MAX_STK", "MAXIMO", "MAX_INV"],
        "SKU": ["SKU", "CODIGO", "COD_PRODUCTO"],
        "DAYS_INVENTORY": ["DAYS_INVENTORY", "DAYS_INV"],
    },
    "clientes": {
        "CLIENT_ID": ["CLIENT_ID", "CLNT_ID", "ID_CLIENTE"],
        "CLIENT_NAME": ["CLIENT_NAME", "CLNT_NAME", "CLIENTE", "NOMBRE_CLI"],
        "CLIENT_ORIGIN": ["CLIENT_ORIGIN", "ORIGEN_CLI", "ORIGEN_CLIENTE", "CLIENT_SOURCE", "INV_SOURCE"],
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
        "TIPO_FACTURA": ["TIPO_FACTURA", "TIPO_FACT", "INV_TYPE", "INVOICE_TYPE"],
        "TIPO_ORDEN": ["TIPO_ORDEN", "TIPO_ORDN", "ORD_TYPE", "ORDER_TYPE"],
        "ORIGEN_VENTA": ["ORIGEN_VENTA", "ORIGEN_VTA", "ORIGEN_VT", "SALE_ORIG"],
        "RECOMM_SOURCE": ["RECOMM_SOURCE", "RECOM_SRC", "ENCUESTA", "RECOMENDACION"],
        "CURRENCY": ["CURRENCY", "MONEDA"],
        "USD_MXN_RATE": [
            "USD_MXN_RATE",
            "TC_MXN_USD",
            "USD_MXN",
            "TIPO_CAMBIO",
            "EXCH_RATE",
            "EXCHANGE_RATE",
        ],
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
        "ORIGEN_VENTA": ["ORIGEN_VENTA", "ORIGEN_VTA", "ORIGEN_VT", "SALE_ORIG"],
        "TIPO_ORDEN": ["TIPO_ORDEN", "TIPO_ORDN", "ORD_TYPE", "ORDER_TYPE"],
        "STATUS": ["STATUS", "ESTATUS"],
        "QTY_ORDER": ["QTY_ORDER", "QTY", "QUANTITY", "CANTIDAD", "CANT"],
        "QTY_PENDING": ["QTY_PENDING", "QTY_PEND", "PENDIENTE", "PEND"],
        "PRICE_MXN": [
            "PRICE_MXN",
            "PRICE",
            "PRC_MXN",
            "PR_MXN",
            "P_MXN",
            "PRICE_MN",
            "PRECIO",
            "PREC_MXN",
            "PRECIO_MXN",
            "UNIT_PRICE",
            "UNIT_PRICE_MXN",
        ],
        "PRICE_USD": ["PRICE_USD", "PRECIO_USD", "PRICE_DLLS", "PRICE_US"],
        "FX_RATE": ["FX_RATE", "USD_MXN_RATE", "USD_MXN", "EXCH_RATE", "EXCHANGE_RATE", "TC", "TIPO_CAMBIO"],
        "ORDER_ID": ["ORDER_ID", "PEDIDO_ID", "ID_PEDIDO"],
        "PRODUCT_NAME": ["PRODUCT_NAME", "PROD_NAME", "PRD_NAME", "PRODUCT_NM", "PRDNAME", "PRODUCTNAME"],
    },
}

STRING_COLUMNS = {"PRODUCT_ID", "PRODUCT_NAME", "BRAND", "CATEGORY", "SELLER_ID", "SELLER_NAME", "VENDOR_ID"}
NUMERIC_COLUMNS = {"EXISTENCIA", "AMOUNT_MXN", "AMOUNT_USD", "STOCK_QTY", "DAYS_INVENTORY"}
DATE_COLUMNS = {"SALE_DATE", "ORDER_DATE", "DATE"}


def _standardize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    return normalize_utils.normalize_cols(df)


def _apply_aliases(df: pd.DataFrame, aliases: dict[str, list[str]]) -> pd.DataFrame:
    return normalize_utils.apply_aliases(df, aliases)


def _ensure_table_columns(df: pd.DataFrame, table_name: str) -> pd.DataFrame:
    defaults: dict[str, object] = {}
    if table_name == "productos":
        defaults = {
            "PRODUCT_ID": "",
            "PRODUCT_NAME": DEFAULT_TEXT,
            "BRAND": DEFAULT_TEXT,
            "CATEGORY": DEFAULT_TEXT,
            "STOCK_QTY": 0,
            "COST_MXN": 0,
            "PRICE_MXN": 0,
        }
    elif table_name == "pedidos":
        defaults = {
            "QTY_PENDING": 0,
            "PRICE_MXN": 0,
        }
    elif table_name == "ventas":
        defaults = {
            "UNIT_PRICE_MXN": 0,
            "PRICE_MXN": 0,
            "USD_MXN_RATE": pd.NA,
        }
    if defaults:
        df = normalize_utils.ensure_columns(df, defaults)
    return df


def normalize_columns(df: pd.DataFrame, table_name: str, source_path: Path) -> pd.DataFrame:
    normalized = _standardize_column_names(df)
    table_aliases = TABLE_ALIASES.get(table_name.lower(), {})
    normalized = _apply_aliases(normalized, table_aliases)
    normalized = _apply_aliases(normalized, COMMON_ALIASES)

    if "PRODUCT_NAME_X" in normalized.columns or "PRODUCT_NAME_Y" in normalized.columns:
        normalized = normalize_utils.coalesce_columns(
            normalized,
            "PRODUCT_NAME",
            ["PRODUCT_NAME", "PRODUCT_NAME_X", "PRODUCT_NAME_Y"],
            drop_candidates=True,
        )

    if table_name.lower() in {"ventas", "productos", "pedidos"}:
        normalized = normalize_utils.coalesce_columns(
            normalized,
            "PRICE_MXN",
            [
                "PRICE_MXN",
                "PRICE",
                "PRC_MXN",
                "PR_MXN",
                "P_MXN",
                "PRICE_MN",
                "PRECIO",
                "PREC_MXN",
                "PRECIO_MXN",
                "UNIT_PRICE",
                "UNIT_PRICE_MXN",
            ],
        )

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

    normalized = _ensure_table_columns(normalized, table_name.lower())
    return normalized


def _read_dbf_to_df(path: Path) -> pd.DataFrame:
    table = DBF(path, load=True, char_decode_errors="ignore")
    df = pd.DataFrame(iter(table))
    return normalize_columns(df, path.stem, path)


def _empty_df() -> pd.DataFrame:
    return pd.DataFrame()


def _safe_read_dbf(path: Path) -> pd.DataFrame:
    if not path.exists():
        return _empty_df()
    return _read_dbf_to_df(path)


def resolve_dbf_dir(default_dir: Path | None = None) -> Path:
    env_value = os.getenv("SAI_ALPHA_DBF_DIR")
    if env_value:
        return Path(env_value)
    if default_dir is None:
        default_dir = Path("data") / "dbf"
    return default_dir


def load_data(dbf_dir: Path) -> DataBundle:
    ventas = _safe_read_dbf(dbf_dir / "ventas.dbf")
    productos = _safe_read_dbf(dbf_dir / "productos.dbf")
    clientes = _safe_read_dbf(dbf_dir / "clientes.dbf")
    vendedores = _safe_read_dbf(dbf_dir / "vendedores.dbf")

    tipo_cambio_path = dbf_dir / "tipo_cambio.dbf"
    tcambio_path = dbf_dir / "tcambio.dbf"
    facturas_path = dbf_dir / "facturas.dbf"
    notas_path = dbf_dir / "notas_credito.dbf"
    pedidos_path = dbf_dir / "pedidos.dbf"

    tipo_cambio = None
    if tipo_cambio_path.exists():
        tipo_cambio = _safe_read_dbf(tipo_cambio_path)
    elif tcambio_path.exists():
        tipo_cambio = _safe_read_dbf(tcambio_path)

    facturas = _safe_read_dbf(facturas_path) if facturas_path.exists() else None
    notas_credito = _safe_read_dbf(notas_path) if notas_path.exists() else None

    pedidos = _safe_read_dbf(pedidos_path) if pedidos_path.exists() else None

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
    if ventas.empty:
        return ventas

    if bundle.tipo_cambio is not None and "USD_MXN_RATE" not in ventas.columns:
        tipo_cambio = bundle.tipo_cambio.copy()
        tipo_cambio = tipo_cambio.rename(columns={"DATE": "SALE_DATE", "USD_MXN": "USD_MXN_RATE"})
        ventas = ventas.merge(tipo_cambio, on="SALE_DATE", how="left")

    ventas = ventas.merge(bundle.productos, on="PRODUCT_ID", how="left", suffixes=("", "_PROD"))
    ventas = ventas.merge(bundle.clientes, on="CLIENT_ID", how="left", suffixes=("", "_CLI"))
    ventas = ventas.merge(bundle.vendedores, on="SELLER_ID", how="left", suffixes=("", "_SELL"))

    ventas = coalesce_columns(
        ventas,
        "PRODUCT_NAME",
        [
            "PRODUCT_NAME",
            "PRODUCT_NAME_X",
            "PRODUCT_NAME_Y",
            "PRODUCT_NAME_PROD",
            "DESCR",
            "DESCRIPTION",
            "NOMBRE",
        ],
        default=DEFAULT_TEXT,
    )
    ventas = coalesce_columns(ventas, "BRAND", ["BRAND", "BRAND_PROD"], default=DEFAULT_TEXT)
    ventas = coalesce_columns(ventas, "CATEGORY", ["CATEGORY", "CATEGORY_PROD"], default=DEFAULT_TEXT)
    ventas = coalesce_columns(ventas, "CLIENT_NAME", ["CLIENT_NAME", "CLIENT_NAME_CLI"], default=DEFAULT_TEXT)
    ventas = coalesce_columns(
        ventas,
        "CLIENT_ORIGIN",
        ["CLIENT_ORIGIN", "CLIENT_ORIGIN_CLI", "CLNT_ORIG", "ORIGEN_CLI"],
        default="Sin información",
    )
    ventas = coalesce_columns(
        ventas,
        "RECOMM_SOURCE",
        ["RECOMM_SOURCE", "RECOMM_SOURCE_CLI", "RECOM_SRC"],
        default="Sin encuesta",
    )
    ventas = coalesce_columns(
        ventas,
        "SELLER_NAME",
        ["SELLER_NAME", "SELLER_NAME_SELL", "SELLER_NM"],
        default=DEFAULT_TEXT,
    )
    ventas = coalesce_columns(
        ventas,
        "ORIGEN_VENTA",
        ["ORIGEN_VENTA", "ORIGEN_VT", "ORIGEN_VTA"],
        default="Mostrador",
    )
    ventas = coalesce_columns(
        ventas,
        "TIPO_FACTURA",
        ["TIPO_FACTURA", "TIPO_FACT"],
        default="Factura",
    )
    ventas = coalesce_columns(
        ventas,
        "TIPO_ORDEN",
        ["TIPO_ORDEN", "TIPO_ORDN"],
        default="Entrega",
    )

    if "SALE_DATE" not in ventas.columns:
        ventas = coalesce_columns(ventas, "SALE_DATE", ["DATE", "FECHA", "FEC", "FECHA_FACTURA"])

    ventas["SALE_DATE"] = pd.to_datetime(ventas.get("SALE_DATE"), errors="coerce")

    ventas = coalesce_columns(
        ventas,
        "USD_MXN_RATE",
        ["USD_MXN_RATE", "USD_MXN", "TC", "TIPO_CAMBIO"],
    )
    if "USD_MXN_RATE" not in ventas.columns:
        ventas["USD_MXN_RATE"] = pd.NA

    if ventas["USD_MXN_RATE"].isna().any():
        day_of_year = ventas["SALE_DATE"].dt.dayofyear.fillna(1)
        ventas["USD_MXN_RATE"] = ventas["USD_MXN_RATE"].fillna(
            17.0 + 0.4 * np.sin(day_of_year / 365 * 6.283)
        )

    ventas = coalesce_columns(
        ventas,
        "CURRENCY",
        ["CURRENCY", "MONEDA"],
        default="MXN",
    )
    ventas["CURRENCY"] = ventas["CURRENCY"].fillna("MXN").astype("string").str.upper()

    ventas = coalesce_columns(
        ventas,
        "TOTAL_MXN",
        ["TOTAL_MXN", "AMOUNT_MXN", "AMT_MXN", "REVENUE_MXN", "SUBT_MXN"],
    )
    ventas = coalesce_columns(
        ventas,
        "TOTAL_USD",
        ["TOTAL_USD", "AMOUNT_USD", "AMT_USD", "REVENUE_USD"],
    )

    ventas = coalesce_columns(ventas, "QTY", ["QTY", "QUANTITY", "CANTIDAD", "CANT"], default=0)
    ventas["QTY"] = pd.to_numeric(ventas["QTY"], errors="coerce").fillna(0)

    ventas = coalesce_columns(
        ventas,
        "UNIT_PRICE_MXN",
        ["UNIT_PRICE_MXN", "UNIT_MXN", "PRECIO", "PRECIO_MXN"],
    )
    ventas["UNIT_PRICE_MXN"] = pd.to_numeric(ventas["UNIT_PRICE_MXN"], errors="coerce")

    if "TOTAL_MXN" not in ventas.columns or ventas["TOTAL_MXN"].isna().all():
        ventas["TOTAL_MXN"] = ventas["UNIT_PRICE_MXN"].fillna(0) * ventas["QTY"].fillna(0)

    if "TOTAL_USD" not in ventas.columns or ventas["TOTAL_USD"].isna().all():
        ventas["TOTAL_USD"] = ventas["TOTAL_MXN"] / ventas["USD_MXN_RATE"].replace(0, pd.NA)

    ventas["REVENUE_MXN"] = pd.to_numeric(ventas["TOTAL_MXN"], errors="coerce").fillna(0)
    ventas["REVENUE_USD"] = pd.to_numeric(ventas["TOTAL_USD"], errors="coerce").fillna(0)

    ventas["UNIT_PRICE_USD"] = ventas["UNIT_PRICE_MXN"] / ventas["USD_MXN_RATE"].replace(0, pd.NA)
    ventas["UNIT_PRICE_USD"] = ventas["UNIT_PRICE_USD"].fillna(ventas["UNIT_PRICE_MXN"].fillna(0))

    ventas = ventas.sort_values("SALE_DATE")
    return ventas


def enrich_pedidos(bundle: DataBundle) -> pd.DataFrame:
    if bundle.pedidos is None:
        return pd.DataFrame()
    pedidos = bundle.pedidos.copy()
    pedidos = pedidos.merge(bundle.productos, on="PRODUCT_ID", how="left", suffixes=("", "_PROD"))
    pedidos = pedidos.merge(bundle.clientes, on="CLIENT_ID", how="left", suffixes=("", "_CLI"))
    pedidos = pedidos.merge(bundle.vendedores, on="SELLER_ID", how="left", suffixes=("", "_SELL"))
    pedidos = coalesce_columns(
        pedidos,
        "PRODUCT_NAME",
        ["PRODUCT_NAME", "PRODUCT_NAME_PROD", "DESCR", "DESCRIPTION", "NOMBRE"],
        default=DEFAULT_TEXT,
    )
    pedidos = coalesce_columns(
        pedidos,
        "CLIENT_NAME",
        ["CLIENT_NAME", "CLIENT_NAME_CLI", "CLNT_NAME"],
        default=DEFAULT_TEXT,
    )
    pedidos = coalesce_columns(
        pedidos,
        "SELLER_NAME",
        ["SELLER_NAME", "SELLER_NAME_SELL", "SELLER_NM"],
        default=DEFAULT_TEXT,
    )
    pedidos = coalesce_columns(
        pedidos,
        "ORDER_DATE",
        ["ORDER_DATE", "DATE", "FECHA", "FEC"],
    )
    pedidos["ORDER_DATE"] = pd.to_datetime(pedidos.get("ORDER_DATE"), errors="coerce")
    pedidos = coalesce_columns(pedidos, "STATUS", ["STATUS", "ESTATUS"], default="Pendiente")
    pedidos = coalesce_columns(
        pedidos,
        "QTY_PENDING",
        ["QTY_PENDING", "QTY_PEND", "PENDIENTE", "PEND"],
        default=0,
    )
    pedidos["QTY_PENDING"] = pd.to_numeric(pedidos["QTY_PENDING"], errors="coerce").fillna(0)
    pedidos = coalesce_columns(
        pedidos,
        "PRICE_MXN",
        ["PRICE_MXN", "PRECIO", "PRECIO_MXN", "UNIT_PRICE", "UNIT_PRICE_MXN"],
        default=0,
    )
    pedidos["PRICE_MXN"] = pd.to_numeric(pedidos["PRICE_MXN"], errors="coerce").fillna(0)
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
