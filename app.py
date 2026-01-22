from __future__ import annotations

from datetime import date, timedelta
from io import BytesIO
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from sai_alpha.etl import enrich_sales, filter_sales, load_data, resolve_dbf_dir
from sai_alpha.mock_data import generate_dbf_dataset


DBF_DIR = resolve_dbf_dir()
USD_RATE = 17.0
REQUIRED_DBF_FILES = ("ventas.dbf", "productos.dbf", "clientes.dbf", "vendedores.dbf")


@st.cache_data(ttl=300, show_spinner=False)
def load_bundle(dbf_dir: Path) -> dict[str, pd.DataFrame | None]:
    bundle = load_data(dbf_dir)
    return {
        "ventas": bundle.ventas,
        "productos": bundle.productos,
        "clientes": bundle.clientes,
        "vendedores": bundle.vendedores,
        "pedidos": bundle.pedidos,
        "tcambio": bundle.tcambio,
    }


@st.cache_data(ttl=300, show_spinner=False)
def load_sales(dbf_dir: Path) -> pd.DataFrame:
    bundle = load_data(dbf_dir)
    return enrich_sales(bundle)


def _export_excel(df: pd.DataFrame) -> tuple[bytes, str, str]:
    buffer = BytesIO()
    try:
        with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False)
        return (
            buffer.getvalue(),
            "xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except ModuleNotFoundError:
        buffer = BytesIO()
        try:
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df.to_excel(writer, index=False)
            return (
                buffer.getvalue(),
                "xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        except ModuleNotFoundError:
            csv_data = df.to_csv(index=False).encode("utf-8")
            return (csv_data, "csv", "text/csv")


def _render_csv_download(label: str, df: pd.DataFrame, filename: str) -> None:
    try:
        csv_data = df.to_csv(index=False).encode("utf-8")
    except Exception as exc:  # noqa: BLE001
        st.error(f"No se pudo generar el CSV: {exc}")
        return
    st.download_button(label, data=csv_data, file_name=filename, mime="text/csv")


def _render_excel_download(label: str, df: pd.DataFrame, filename_base: str) -> None:
    try:
        data, extension, mime = _export_excel(df)
    except Exception as exc:  # noqa: BLE001
        st.error(f"No se pudo generar el Excel: {exc}")
        return
    if extension == "csv":
        st.warning("No se encontraron motores Excel; se exportará un CSV.")
    st.download_button(label, data=data, file_name=f"{filename_base}.{extension}", mime=mime)


def _build_inventory(productos: pd.DataFrame) -> pd.DataFrame:
    inventory = productos.copy()
    inventory["ON_HAND"] = (inventory["PRODUCT_ID"].astype(int) * 7) % 120 + 20
    inventory["INVENTORY_MXN"] = inventory["ON_HAND"] * inventory["BASE_PRICE"].astype(float)
    return inventory


def _get_week_options(ventas: pd.DataFrame, start: date, end: date) -> list[int]:
    scoped = ventas[(ventas["SALE_DATE"] >= pd.Timestamp(start)) & (ventas["SALE_DATE"] <= pd.Timestamp(end))]
    weeks = scoped["SALE_DATE"].dt.isocalendar().week.unique()
    return sorted(int(week) for week in weeks)


def _apply_week_filter(ventas: pd.DataFrame, weeks: list[int]) -> pd.DataFrame:
    if not weeks:
        return ventas
    return ventas[ventas["SALE_DATE"].dt.isocalendar().week.isin(weeks)]


def _sidebar_filters(ventas: pd.DataFrame) -> dict:
    st.sidebar.title("Filtros")
    page = st.sidebar.selectbox("Página", ["Ventas", "Clientes", "Productos"], index=0)

    min_date = ventas["SALE_DATE"].min().date()
    max_date = ventas["SALE_DATE"].max().date()
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
    selected_brands = st.sidebar.multiselect("Marcas", brand_options, default=brand_options)
    selected_vendors = st.sidebar.multiselect("Vendedor", vendor_options, default=vendor_options)

    week_options = _get_week_options(ventas, start, end)
    selected_weeks = st.sidebar.multiselect("Semana del año", week_options, default=week_options)

    granularity = None
    if page == "Ventas":
        granularity = st.sidebar.selectbox("Granularidad serie", ["Diario", "Semanal", "Mensual"], index=1)

    return {
        "page": page,
        "date_range": (start, end),
        "brands": selected_brands,
        "vendors": selected_vendors,
        "weeks": selected_weeks,
        "granularity": granularity,
    }


def _trend_orders(
    ventas: pd.DataFrame,
    start: date,
    end: date,
    brands: list[str],
    vendors: list[str],
) -> tuple[int, float]:
    current = filter_sales(ventas, (pd.Timestamp(start), pd.Timestamp(end)), brands, vendors)
    current_orders = current["SALE_ID"].nunique()

    period_days = (end - start).days + 1
    prev_end = start - timedelta(days=1)
    prev_start = start - timedelta(days=period_days)
    previous = filter_sales(ventas, (pd.Timestamp(prev_start), pd.Timestamp(prev_end)), brands, vendors)
    previous_orders = previous["SALE_ID"].nunique()

    if previous_orders == 0:
        return current_orders, 0.0
    delta = (current_orders - previous_orders) / previous_orders * 100
    return current_orders, delta


def render_ventas(ventas: pd.DataFrame, filters: dict, pedidos: pd.DataFrame | None) -> None:
    start, end = filters["date_range"]
    filtered = filter_sales(ventas, (pd.Timestamp(start), pd.Timestamp(end)), filters["brands"], filters["vendors"])
    filtered = _apply_week_filter(filtered, filters["weeks"])
    filtered = filtered.copy()

    st.header("Ventas")
    total_revenue = filtered["REVENUE"].sum()
    current_orders, delta_orders = _trend_orders(ventas, start, end, filters["brands"], filters["vendors"])
    last_date = filtered["SALE_DATE"].max() if not filtered.empty else pd.Timestamp(end)
    last_week = last_date - timedelta(days=6)
    if pedidos is not None and not pedidos.empty and "STATUS" in pedidos.columns:
        pending_scope = pedidos[
            (pedidos["ORDER_DATE"] >= pd.Timestamp(start))
            & (pedidos["ORDER_DATE"] <= pd.Timestamp(end))
            & (pedidos["STATUS"].isin(["Pendiente", "Parcial"]))
        ]
        pending_orders = pending_scope["ORDER_ID"].nunique()
    else:
        pending_orders = (
            filtered[filtered["SALE_DATE"] >= last_week]["SALE_ID"].nunique() if not filtered.empty else 0
        )

    col1, col2, col3 = st.columns(3)
    col1.metric("Facturación (MXN)", f"$ {total_revenue:,.2f}")
    col2.metric("Tendencia pedidos", f"{current_orders:,}", delta=f"{delta_orders:+.1f}%")
    col3.metric("Pedidos por surtir", f"{pending_orders:,}")

    st.subheader("Tabla por vendedor")
    if filtered.empty:
        st.info("No hay registros para los filtros seleccionados.")
        return

    days_count = filtered["SALE_DATE"].nunique()
    vendor_table = (
        filtered.groupby("VENDOR_NAME")
        .agg(
            TOTAL_MXN=("REVENUE", "sum"),
            FACTURAS=("SALE_ID", "nunique"),
            PEDIDOS=("SALE_ID", "count"),
        )
        .reset_index()
    )
    vendor_table["PROMEDIO_DIARIO_MXN"] = vendor_table["TOTAL_MXN"] / max(days_count, 1)
    vendor_table = vendor_table.sort_values(by="TOTAL_MXN", ascending=False)
    vendor_table = vendor_table[
        ["VENDOR_NAME", "TOTAL_MXN", "PROMEDIO_DIARIO_MXN", "FACTURAS", "PEDIDOS"]
    ].rename(
        columns={
            "VENDOR_NAME": "VENDEDOR",
            "FACTURAS": "#FACTURAS",
            "PEDIDOS": "#PEDIDOS",
        }
    )

    st.dataframe(vendor_table, use_container_width=True)

    st.subheader("Comparativo por vendedor")
    bar_fig = px.bar(
        vendor_table,
        x="VENDEDOR",
        y="TOTAL_MXN",
        color="VENDEDOR",
        text_auto=".2s",
        labels={"TOTAL_MXN": "Total (MXN)"},
    )
    bar_fig.update_layout(showlegend=False, height=380)
    st.plotly_chart(bar_fig, use_container_width=True)

    st.subheader("Serie de tiempo por vendedor")
    granularity = filters["granularity"] or "Semanal"
    if granularity == "Diario":
        filtered["PERIODO"] = filtered["SALE_DATE"].dt.date
    elif granularity == "Mensual":
        filtered["PERIODO"] = filtered["SALE_DATE"].dt.to_period("M").dt.start_time
    else:
        filtered["PERIODO"] = filtered["SALE_DATE"].dt.to_period("W").dt.start_time

    series = (
        filtered.groupby(["PERIODO", "VENDOR_NAME"])["REVENUE"].sum().reset_index().sort_values("PERIODO")
    )
    line_fig = px.line(
        series,
        x="PERIODO",
        y="REVENUE",
        color="VENDOR_NAME",
        markers=True,
        labels={"REVENUE": "MXN", "VENDOR_NAME": "Vendedor"},
    )
    line_fig.update_layout(height=420)
    st.plotly_chart(line_fig, use_container_width=True)

    st.subheader("Exportaciones")
    col_csv, col_excel, col_series = st.columns(3)
    with col_csv:
        _render_csv_download("Exportar tabla CSV", vendor_table, "ventas_vendedor.csv")
    with col_excel:
        _render_excel_download("Exportar tabla Excel", vendor_table, "ventas_vendedor")
    with col_series:
        _render_csv_download("Exportar serie CSV", series, "ventas_serie.csv")


def render_clientes(ventas: pd.DataFrame, filters: dict) -> None:
    start, end = filters["date_range"]
    filtered = filter_sales(ventas, (pd.Timestamp(start), pd.Timestamp(end)), filters["brands"], filters["vendors"])
    filtered = _apply_week_filter(filtered, filters["weeks"])
    filtered = filtered.copy()

    st.header("Clientes")
    total_mxn = filtered["REVENUE"].sum()
    if "REVENUE_USD" in filtered.columns:
        total_usd = filtered["REVENUE_USD"].sum()
    elif "TC_MXN_USD" in filtered.columns:
        total_usd = (filtered["REVENUE"] / filtered["TC_MXN_USD"]).sum()
    else:
        total_usd = total_mxn / USD_RATE
    distinct_clients = filtered["CLIENT_ID"].nunique()

    col1, col2, col3 = st.columns(3)
    col1.metric("Clientes MXN", f"$ {total_mxn:,.2f}")
    col2.metric("Clientes USD", f"$ {total_usd:,.2f}")
    col3.metric("Clientes distintos con facturas", f"{distinct_clients:,}")

    st.subheader("Tabla de clientes")
    if filtered.empty:
        st.info("No hay registros para los filtros seleccionados.")
        return

    client_table = (
        filtered.groupby(["CLIENT_ID", "CLIENT_NAME"])
        .agg(
            TOTAL_MXN=("REVENUE", "sum"),
            LAST_PURCHASE=("SALE_DATE", "max"),
            INVOICES=("SALE_ID", "nunique"),
            AVG_TICKET=("REVENUE", "mean"),
        )
        .reset_index()
        .sort_values(by="TOTAL_MXN", ascending=False)
    )
    client_table["LAST_PURCHASE"] = client_table["LAST_PURCHASE"].dt.date

    st.dataframe(client_table, use_container_width=True)

    st.subheader("Desglose por ORIGIN")
    origin_column = "ORIGEN_CLI" if "ORIGEN_CLI" in filtered.columns else "REGION"
    if "REVENUE_USD" in filtered.columns:
        usd_series = filtered["REVENUE_USD"]
    elif "TC_MXN_USD" in filtered.columns:
        usd_series = filtered["REVENUE"] / filtered["TC_MXN_USD"]
    else:
        usd_series = filtered["REVENUE"] / USD_RATE
    origin_data = (
        filtered.assign(ORIGIN=filtered[origin_column], USD=usd_series)
        .groupby("ORIGIN")
        .agg(
            CLIENTES=("CLIENT_ID", "nunique"),
            FACTURAS=("SALE_ID", "nunique"),
            MXN=("REVENUE", "sum"),
            USD=("USD", "sum"),
        )
        .reset_index()
    )

    col_a, col_b = st.columns(2)
    with col_a:
        fig_clients = px.bar(origin_data, x="ORIGIN", y="CLIENTES", text_auto=True, title="Conteo clientes")
        fig_clients.update_layout(height=320)
        st.plotly_chart(fig_clients, use_container_width=True)
        fig_mxn = px.bar(origin_data, x="ORIGIN", y="MXN", text_auto=".2s", title="Monto MXN")
        fig_mxn.update_layout(height=320)
        st.plotly_chart(fig_mxn, use_container_width=True)
    with col_b:
        fig_invoices = px.bar(origin_data, x="ORIGIN", y="FACTURAS", text_auto=True, title="Conteo facturas")
        fig_invoices.update_layout(height=320)
        st.plotly_chart(fig_invoices, use_container_width=True)
        fig_usd = px.bar(origin_data, x="ORIGIN", y="USD", text_auto=".2s", title="Monto USD")
        fig_usd.update_layout(height=320)
        st.plotly_chart(fig_usd, use_container_width=True)

    st.subheader("Exportaciones")
    col_csv, col_excel = st.columns(2)
    with col_csv:
        _render_csv_download("Exportar CSV", client_table, "clientes.csv")
    with col_excel:
        _render_excel_download("Exportar Excel", client_table, "clientes")


def render_productos(ventas: pd.DataFrame, productos: pd.DataFrame, filters: dict) -> None:
    start, end = filters["date_range"]
    filtered = filter_sales(ventas, (pd.Timestamp(start), pd.Timestamp(end)), filters["brands"], filters["vendors"])
    filtered = _apply_week_filter(filtered, filters["weeks"])
    filtered = filtered.copy()

    inventory = _build_inventory(productos)
    if filters["brands"]:
        inventory = inventory[inventory["BRAND"].isin(filters["brands"])]

    st.header("Productos")

    sold_units = filtered.groupby("PRODUCT_ID")["QUANTITY"].sum().reset_index()
    merged = inventory.merge(sold_units, on="PRODUCT_ID", how="left").rename(columns={"QUANTITY": "SOLD_UNITS"})
    merged["SOLD_UNITS"] = merged["SOLD_UNITS"].fillna(0)
    merged["SOLD_MXN"] = merged["SOLD_UNITS"] * merged["BASE_PRICE"].astype(float)
    merged["ROTATION"] = merged["SOLD_UNITS"] / merged["ON_HAND"].replace(0, 1)

    rotation_avg = merged["ROTATION"].mean() if not merged.empty else 0
    inventory_value = merged["INVENTORY_MXN"].sum()

    col1, col2 = st.columns(2)
    col1.metric("Rotación promedio", f"{rotation_avg:.2f}x")
    col2.metric("Valor inventario (MXN)", f"$ {inventory_value:,.2f}")

    st.subheader("Pareto Top 10 por unidades")
    pareto = merged.sort_values(by="SOLD_UNITS", ascending=False).head(10)
    pareto_table = pareto[["PRODUCT_NAME", "ON_HAND", "SOLD_UNITS", "SOLD_MXN"]]
    st.dataframe(pareto_table, use_container_width=True)
    pareto_fig = px.bar(
        pareto,
        x="PRODUCT_NAME",
        y="SOLD_UNITS",
        text_auto=True,
        labels={"SOLD_UNITS": "Unidades"},
    )
    pareto_fig.update_layout(height=360)
    st.plotly_chart(pareto_fig, use_container_width=True)

    st.subheader("Tabla stock por ventas mensuales")
    last_date = filtered["SALE_DATE"].max() if not filtered.empty else pd.Timestamp(end)
    month_start = last_date - pd.DateOffset(days=30)
    monthly_sales = (
        filtered[filtered["SALE_DATE"] >= month_start]
        .groupby("PRODUCT_ID")
        .agg(SALES_MONTH_UNITS=("QUANTITY", "sum"), SALES_MONTH_MXN=("REVENUE", "sum"))
        .reset_index()
    )
    stock_table = (
        inventory.merge(monthly_sales, on="PRODUCT_ID", how="left")
        .fillna({"SALES_MONTH_UNITS": 0, "SALES_MONTH_MXN": 0})
        .sort_values(by=["SALES_MONTH_UNITS", "SALES_MONTH_MXN"], ascending=False)
    )
    stock_table_view = stock_table[
        [
            "SKU",
            "PRODUCT_NAME",
            "BRAND",
            "CATEGORY",
            "ON_HAND",
            "INVENTORY_MXN",
            "SALES_MONTH_UNITS",
            "SALES_MONTH_MXN",
        ]
    ]
    st.dataframe(stock_table_view, use_container_width=True)

    st.subheader("Tabla rotación por producto")
    rotation_table = merged[["SKU", "PRODUCT_NAME", "ON_HAND", "SOLD_UNITS", "ROTATION"]].sort_values(
        by="ROTATION", ascending=False
    )
    st.dataframe(rotation_table, use_container_width=True)

    st.subheader("Exportaciones")
    col_excel, col_csv = st.columns(2)
    with col_excel:
        _render_excel_download("Exportar stock Excel", stock_table_view, "stock")
    with col_csv:
        _render_csv_download("Exportar rotación CSV", rotation_table, "rotacion.csv")


def _get_dbf_files(dbf_dir: Path) -> list[Path]:
    if not dbf_dir.exists():
        return []
    return sorted(dbf_dir.glob("*.dbf"))


def _generate_dbfs(dbf_dir: Path) -> None:
    generate_dbf_dataset(dbf_dir)


def _get_missing_dbfs(dbf_dir: Path) -> list[str]:
    return [name for name in REQUIRED_DBF_FILES if not (dbf_dir / name).exists()]


def main() -> None:
    st.set_page_config(page_title="SAI Alpha Dashboard", page_icon="📊", layout="wide")
    st.title("Dashboard Ejecutivo y Operativo - SAI Alpha")
    st.caption("Vista integrada de ventas, clientes y productos")

    dbf_dir = DBF_DIR
    dbf_dir.mkdir(parents=True, exist_ok=True)
    dbf_files = _get_dbf_files(dbf_dir)
    missing_dbfs = _get_missing_dbfs(dbf_dir)
    generation_error: str | None = None
    auto_generated = False

    if missing_dbfs:
        with st.spinner("Generando datos mock..."):
            try:
                _generate_dbfs(dbf_dir)
                auto_generated = True
            except Exception as exc:  # noqa: BLE001
                generation_error = str(exc)
        dbf_files = _get_dbf_files(dbf_dir)
        missing_dbfs = _get_missing_dbfs(dbf_dir)

    if generation_error:
        st.error(f"No se pudieron generar los DBF automáticamente: {generation_error}")
    elif auto_generated:
        st.success("Datos mock generados automáticamente.")

    if not missing_dbfs:
        st.info(f"DBF dir: {dbf_dir}\nDBF files: {len(dbf_files)}")
    else:
        missing_list = ", ".join(missing_dbfs)
        st.warning(
            f"No se encontraron todos los DBF requeridos.\nDBF dir: {dbf_dir}\nFaltantes: {missing_list}"
        )
        if st.button("Generar datos mock"):
            with st.spinner("Generando datos mock..."):
                try:
                    _generate_dbfs(dbf_dir)
                except Exception as exc:  # noqa: BLE001
                    st.error(f"No se pudieron generar los DBF: {exc}")
                else:
                    st.success("Datos mock generados.")
                    st.rerun()
        st.stop()

    ventas = load_sales(dbf_dir)
    bundle = load_bundle(dbf_dir)

    if ventas.empty:
        st.error("No hay datos disponibles. Ejecuta generate_dbfs.py para crear data DBF.")
        return

    filters = _sidebar_filters(ventas)

    if filters["page"] == "Ventas":
        render_ventas(ventas, filters, bundle.get("pedidos"))
    elif filters["page"] == "Clientes":
        render_clientes(ventas, filters)
    else:
        render_productos(ventas, bundle["productos"], filters)


if __name__ == "__main__":
    main()
