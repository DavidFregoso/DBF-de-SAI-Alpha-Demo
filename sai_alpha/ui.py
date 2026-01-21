from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from sai_alpha.etl import DataBundle, enrich_sales, filter_sales, load_data

DATA_DIR = Path("data/dbf")
EXPORT_DIR = Path("data/exports")


@st.cache_data(show_spinner=False)
def load_bundle() -> DataBundle:
    return load_data(DATA_DIR)


@st.cache_data(show_spinner=False)
def load_sales() -> pd.DataFrame:
    bundle = load_bundle()
    return enrich_sales(bundle)


def sidebar_filters(ventas: pd.DataFrame) -> pd.DataFrame:
    min_date = ventas["SALE_DATE"].min()
    max_date = ventas["SALE_DATE"].max()
    st.sidebar.header("Filtros")
    date_range = st.sidebar.date_input(
        "Rango de fechas",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if isinstance(date_range, tuple):
        start, end = date_range
    else:
        start, end = min_date, max_date
    brand_options = sorted(ventas["BRAND"].dropna().unique())
    vendor_options = sorted(ventas["VENDOR_NAME"].dropna().unique())
    selected_brands = st.sidebar.multiselect("Marca", brand_options, default=brand_options)
    selected_vendors = st.sidebar.multiselect("Vendedor", vendor_options, default=vendor_options)
    filtered = filter_sales(ventas, (pd.Timestamp(start), pd.Timestamp(end)), selected_brands, selected_vendors)
    st.sidebar.caption(f"Registros filtrados: {len(filtered):,}")
    return filtered


def export_buttons(df: pd.DataFrame, label: str) -> None:
    csv_data = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=f"Descargar {label} CSV",
        data=csv_data,
        file_name=f"{label}.csv",
        mime="text/csv",
    )
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    excel_path = EXPORT_DIR / f"{label}.xlsx"
    df.to_excel(excel_path, index=False)
    with open(excel_path, "rb") as excel_file:
        st.download_button(
            label=f"Descargar {label} Excel",
            data=excel_file,
            file_name=f"{label}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
