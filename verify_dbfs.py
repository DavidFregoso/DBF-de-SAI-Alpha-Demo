from __future__ import annotations

from pathlib import Path

import pandas as pd

from sai_alpha.etl import load_data, resolve_dbf_dir
from sai_alpha.mock_data import generate_dbf_dataset


EXPECTED_COLUMNS = {
    "ventas": {
        "SALE_ID",
        "FACTURA_ID",
        "SALE_DATE",
        "PRODUCT_ID",
        "PRODUCT_NAME",
        "BRAND",
        "CATEGORY",
        "CLIENT_ID",
        "CLIENT_NAME",
        "CLIENT_ORIGIN",
        "SELLER_ID",
        "SELLER_NAME",
        "ORIGEN_VENTA",
        "RECOMM_SOURCE",
        "TIPO_FACTURA",
        "TIPO_ORDEN",
        "STATUS",
        "QTY",
        "UNIT_PRICE_MXN",
        "AMOUNT_MXN",
        "CURRENCY",
        "USD_MXN_RATE",
    },
    "productos": {"PRODUCT_ID", "SKU", "PRODUCT_NAME", "BRAND", "CATEGORY", "COST_MXN", "PRICE_MXN", "STOCK_QTY"},
    "clientes": {"CLIENT_ID", "CLIENT_NAME", "CLIENT_ORIGIN", "RECOMM_SOURCE"},
    "vendedores": {"SELLER_ID", "SELLER_NAME"},
    "tipo_cambio": {"DATE", "USD_MXN"},
    "facturas": {"FACTURA_ID", "FECHA", "CLIENT_ID", "SELLER_ID", "STATUS", "TIPO_FACTURA"},
    "notas_credito": {"NOTA_ID", "FACTURA_ID", "FECHA", "MONTO_MXN"},
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
        "tipo_cambio": bundle.tipo_cambio,
        "facturas": bundle.facturas,
        "notas_credito": bundle.notas_credito,
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
