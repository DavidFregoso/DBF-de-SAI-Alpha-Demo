from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from dbfread import DBF


@dataclass
class DataBundle:
    ventas: pd.DataFrame
    clientes: pd.DataFrame
    productos: pd.DataFrame
    vendedores: pd.DataFrame
    pedidos: pd.DataFrame


def _read_dbf(path: Path) -> pd.DataFrame:
    table = DBF(path, load=True, char_decode_errors="ignore")
    df = pd.DataFrame(iter(table))
    if "SALE_DATE" in df.columns:
        df["SALE_DATE"] = pd.to_datetime(df["SALE_DATE"])
    if "PEDIDO_DATE" in df.columns:
        df["PEDIDO_DATE"] = pd.to_datetime(df["PEDIDO_DATE"])
    return df


def load_bundle(dbf_dir: Path) -> DataBundle:
    ventas = _read_dbf(dbf_dir / "VENTAS.DBF")
    clientes = _read_dbf(dbf_dir / "CLIENTES.DBF")
    productos = _read_dbf(dbf_dir / "PRODUCTOS.DBF")
    vendedores = _read_dbf(dbf_dir / "VENDEDORES.DBF")
    pedidos = _read_dbf(dbf_dir / "PEDIDOS.DBF")
    return DataBundle(ventas=ventas, clientes=clientes, productos=productos, vendedores=vendedores, pedidos=pedidos)


def enrich_sales(bundle: DataBundle) -> pd.DataFrame:
    ventas = bundle.ventas.copy()
    ventas = ventas.merge(bundle.clientes, on="CLIENT_ID", how="left", suffixes=("", "_CLI"))
    ventas = ventas.merge(bundle.productos, on="PRODUCT_ID", how="left", suffixes=("", "_PROD"))
    ventas = ventas.merge(bundle.vendedores, on="VENDOR_ID", how="left", suffixes=("", "_VEND"))
    ventas["TOTAL_MXN"] = ventas["TOTAL_MXN"].astype(float)
    ventas["TOTAL_USD"] = ventas["TOTAL_USD"].astype(float)
    ventas["QUANTITY"] = ventas["QUANTITY"].astype(int)
    ventas["WEEK"] = ventas["SALE_DATE"].dt.isocalendar().week.astype(int)
    return ventas


def filter_sales(
    ventas: pd.DataFrame,
    date_range: tuple[pd.Timestamp, pd.Timestamp] | None,
    brands: list[str],
    vendors: list[str],
    weeks: list[int],
) -> pd.DataFrame:
    df = ventas.copy()
    if date_range:
        start, end = date_range
        df = df[(df["SALE_DATE"] >= start) & (df["SALE_DATE"] <= end)]
    if brands:
        df = df[df["BRAND"].isin(brands)]
    if vendors:
        df = df[df["VENDOR_NAME"].isin(vendors)]
    if weeks:
        df = df[df["WEEK"].isin(weeks)]
    return df
