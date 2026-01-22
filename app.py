from __future__ import annotations

import streamlit as st

from sai_alpha.etl import resolve_dbf_dir
from sai_alpha.ui import REQUIRED_SALES_COLUMNS, load_bundle, load_sales


def _assert_required_columns(df, required, label) -> str:
    missing = sorted(required - set(df.columns))
    assert not missing, f"[schema check] Missing columns in {label}: {', '.join(missing)}"
    return f"{label}: OK"


def _validate_product_schema(productos) -> None:
    if "PRODUCT_NAME" in productos.columns:
        return
    dbf_dir = resolve_dbf_dir()
    st.error("Falta la columna PRODUCT_NAME en el inventario (productos).")
    st.write("DBF cargado:", str(dbf_dir / "productos.dbf"))
    st.write("Columnas disponibles:", list(productos.columns))
    st.stop()


def _run_schema_checks() -> None:
    bundle = load_bundle()
    ventas = load_sales()
    _validate_product_schema(bundle.productos)
    results = [
        _assert_required_columns(ventas, REQUIRED_SALES_COLUMNS, "ventas"),
        _assert_required_columns(
            bundle.productos,
            {"PRODUCT_ID", "PRODUCT_NAME", "BRAND", "CATEGORY", "STOCK_QTY"},
            "productos",
        ),
    ]
    if bundle.pedidos is not None and not bundle.pedidos.empty:
        results.append(
            _assert_required_columns(
                bundle.pedidos,
                {"ORDER_ID", "PRODUCT_ID", "PRODUCT_NAME", "ORDER_DATE"},
                "pedidos",
            )
        )
    st.caption("Schema check: " + " | ".join(results))


st.set_page_config(page_title="Demo Tienda – Dashboard Ejecutivo", page_icon="🛒", layout="wide")
_run_schema_checks()
st.switch_page("pages/1_Resumen Ejecutivo.py")
