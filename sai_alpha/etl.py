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
    tcambio: pd.DataFrame | None = None
    pedidos: pd.DataFrame | None = None


def _read_dbf_to_df(path: Path) -> pd.DataFrame:
    table = DBF(path, load=True, char_decode_errors="ignore")
    df = pd.DataFrame(iter(table))
    if "SALE_DATE" in df.columns:
        df["SALE_DATE"] = pd.to_datetime(df["SALE_DATE"])
    if "ORDER_DATE" in df.columns:
        df["ORDER_DATE"] = pd.to_datetime(df["ORDER_DATE"])
    if "FECHA" in df.columns:
        df["FECHA"] = pd.to_datetime(df["FECHA"])
    return df


def resolve_dbf_dir(default_dir: Path | None = None) -> Path:
    env_value = os.getenv("SAI_ALPHA_DBF_DIR")
    if env_value:
        return Path(env_value)
    if default_dir is None:
        default_dir = Path("data") / "dbf"
    return default_dir


def load_data(dbf_dir: Path) -> DataBundle:
    ventas = _read_dbf_to_df(dbf_dir / "ventas.dbf").rename(
        columns={"REV_USD": "REVENUE_USD"}, errors="ignore"
    )
    productos = _read_dbf_to_df(dbf_dir / "productos.dbf").rename(
        columns={"PROD_NAME": "PRODUCT_NAME"}, errors="ignore"
    )
    clientes = _read_dbf_to_df(dbf_dir / "clientes.dbf").rename(
        columns={"CLNT_NAME": "CLIENT_NAME", "LAST_PURCH": "LAST_PURCHASE"}, errors="ignore"
    )
    vendedores = _read_dbf_to_df(dbf_dir / "vendedores.dbf").rename(
        columns={"VEND_NAME": "VENDOR_NAME"}, errors="ignore"
    )
    tcambio_path = dbf_dir / "tcambio.dbf"
    pedidos_path = dbf_dir / "pedidos.dbf"
    tcambio = _read_dbf_to_df(tcambio_path) if tcambio_path.exists() else None
    pedidos = (
        _read_dbf_to_df(pedidos_path).rename(columns={"QTY_PEND": "QTY_PENDING"}, errors="ignore")
        if pedidos_path.exists()
        else None
    )

    return DataBundle(
        ventas=ventas,
        productos=productos,
        clientes=clientes,
        vendedores=vendedores,
        tcambio=tcambio,
        pedidos=pedidos,
    )


def enrich_sales(bundle: DataBundle) -> pd.DataFrame:
    ventas = bundle.ventas.copy()
    if bundle.tcambio is not None and "TC_MXN_USD" not in ventas.columns:
        ventas = ventas.merge(
            bundle.tcambio.rename(columns={"FECHA": "SALE_DATE"}),
            on="SALE_DATE",
            how="left",
        )
    ventas = ventas.merge(bundle.productos, on="PRODUCT_ID", how="left", suffixes=("", "_PROD"))
    ventas = ventas.merge(bundle.clientes, on="CLIENT_ID", how="left", suffixes=("", "_CLI"))
    ventas = ventas.merge(bundle.vendedores, on="VENDOR_ID", how="left", suffixes=("", "_VEND"))
    if "TC_MXN_USD" in ventas.columns:
        ventas["TC_MXN_USD"] = ventas["TC_MXN_USD"].astype(float)
    ventas["REVENUE"] = ventas["REVENUE"].astype(float)
    ventas["QUANTITY"] = ventas["QUANTITY"].astype(int)
    ventas["UNIT_PRICE"] = ventas["UNIT_PRICE"].astype(float)
    if "MONEDA" in ventas.columns:
        if "REVENUE_USD" not in ventas.columns and "TC_MXN_USD" in ventas.columns:
            ventas["REVENUE_USD"] = ventas["REVENUE"] / ventas["TC_MXN_USD"]
        ventas["REVENUE_MXN"] = ventas["REVENUE"]
        if "REVENUE_USD" in ventas.columns:
            ventas["REVENUE_USD"] = ventas["REVENUE_USD"].astype(float)
    return ventas


def enrich_pedidos(bundle: DataBundle) -> pd.DataFrame:
    if bundle.pedidos is None:
        return pd.DataFrame()
    pedidos = bundle.pedidos.copy()
    pedidos = pedidos.merge(bundle.productos, on="PRODUCT_ID", how="left", suffixes=("", "_PROD"))
    pedidos = pedidos.merge(bundle.clientes, on="CLIENT_ID", how="left", suffixes=("", "_CLI"))
    pedidos = pedidos.merge(bundle.vendedores, on="VENDOR_ID", how="left", suffixes=("", "_VEND"))
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
        df = df[df["VENDOR_NAME"].isin(vendors)]
    return df
