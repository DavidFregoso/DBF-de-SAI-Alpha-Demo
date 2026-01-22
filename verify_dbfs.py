from __future__ import annotations

from pathlib import Path

import pandas as pd

from sai_alpha.etl import load_data, resolve_dbf_dir
from sai_alpha.mock_data import generate_dbf_dataset


EXPECTED_COLUMNS = {
    "ventas": {
        "SALE_ID",
        "SALE_DATE",
        "PRODUCT_ID",
        "CLIENT_ID",
        "VENDOR_ID",
        "MONEDA",
        "TC_MXN_USD",
        "REVENUE",
    },
    "productos": {"PRODUCT_ID", "SKU", "PRODUCT_NAME", "BRAND", "EXISTENCIA"},
    "clientes": {"CLIENT_ID", "CLIENT_NAME", "ORIGEN_CLI", "CHANNEL"},
    "vendedores": {"VENDOR_ID", "VENDOR_NAME"},
    "tcambio": {"FECHA", "TC_MXN_USD"},
    "pedidos": {"ORDER_ID", "ORDER_DATE", "STATUS", "QTY_PENDING"},
}


def _ensure_columns(df: pd.DataFrame, required: set[str], name: str) -> None:
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Faltan columnas en {name}: {sorted(missing)}")


def main() -> None:
    dbf_dir = resolve_dbf_dir()
    dbf_dir.mkdir(parents=True, exist_ok=True)
    generate_dbf_dataset(dbf_dir)

    bundle = load_data(dbf_dir)
    tables: dict[str, pd.DataFrame | None] = {
        "ventas": bundle.ventas,
        "productos": bundle.productos,
        "clientes": bundle.clientes,
        "vendedores": bundle.vendedores,
        "tcambio": bundle.tcambio,
        "pedidos": bundle.pedidos,
    }

    print(f"DBF dir: {Path(dbf_dir).resolve()}")
    for name, df in tables.items():
        if df is None:
            raise ValueError(f"No se encontró la tabla {name}.")
        _ensure_columns(df, EXPECTED_COLUMNS[name], name)
        print(f"- {name}: {len(df):,} filas")


if __name__ == "__main__":
    main()
