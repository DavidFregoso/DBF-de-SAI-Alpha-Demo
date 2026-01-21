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


def _read_dbf_to_df(path: Path) -> pd.DataFrame:
    table = DBF(path, load=True, char_decode_errors="ignore")
    df = pd.DataFrame(iter(table))
    if "SALE_DATE" in df.columns:
        df["SALE_DATE"] = pd.to_datetime(df["SALE_DATE"])
    return df


def resolve_dbf_dir(default_dir: Path | None = None) -> Path:
    if default_dir is None:
        default_dir = Path.cwd() / "data" / "dbf"
    env_value = os.getenv("SAI_DBF_DIR")
    return Path(env_value) if env_value else default_dir


def load_data(dbf_dir: Path) -> DataBundle:
    ventas = _read_dbf_to_df(dbf_dir / "ventas.dbf")
    productos = _read_dbf_to_df(dbf_dir / "productos.dbf").rename(
        columns={"PROD_NAME": "PRODUCT_NAME"}, errors="ignore"
    )
    clientes = _read_dbf_to_df(dbf_dir / "clientes.dbf").rename(
        columns={"CLNT_NAME": "CLIENT_NAME"}, errors="ignore"
    )
    vendedores = _read_dbf_to_df(dbf_dir / "vendedores.dbf").rename(
        columns={"VEND_NAME": "VENDOR_NAME"}, errors="ignore"
    )

    return DataBundle(ventas=ventas, productos=productos, clientes=clientes, vendedores=vendedores)


def enrich_sales(bundle: DataBundle) -> pd.DataFrame:
    ventas = bundle.ventas.copy()
    ventas = ventas.merge(bundle.productos, on="PRODUCT_ID", how="left", suffixes=("", "_PROD"))
    ventas = ventas.merge(bundle.clientes, on="CLIENT_ID", how="left", suffixes=("", "_CLI"))
    ventas = ventas.merge(bundle.vendedores, on="VENDOR_ID", how="left", suffixes=("", "_VEND"))
    ventas["REVENUE"] = ventas["REVENUE"].astype(float)
    ventas["QUANTITY"] = ventas["QUANTITY"].astype(int)
    ventas["UNIT_PRICE"] = ventas["UNIT_PRICE"].astype(float)
    return ventas


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
