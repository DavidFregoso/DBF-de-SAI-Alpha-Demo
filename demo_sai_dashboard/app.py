from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from etl import DataBundle, enrich_sales, filter_sales, load_bundle

DBF_DIR = Path("dbf")
EXPORT_DIR = Path("exports")


@st.cache_data(show_spinner=False)
def load_data() -> DataBundle:
    return load_bundle(DBF_DIR)


@st.cache_data(show_spinner=False)
def load_sales() -> pd.DataFrame:
    bundle = load_data()
    return enrich_sales(bundle)


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


def sidebar_filters(ventas: pd.DataFrame) -> pd.DataFrame:
    st.sidebar.header("Filtros")
    min_date = ventas["SALE_DATE"].min()
    max_date = ventas["SALE_DATE"].max()
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
    week_options = sorted(ventas["WEEK"].dropna().unique())

    selected_brands = st.sidebar.multiselect("Marcas", brand_options, default=brand_options)
    selected_vendors = st.sidebar.multiselect("Vendedor", vendor_options, default=vendor_options)
    selected_weeks = st.sidebar.multiselect("Semana del año", week_options, default=week_options)

    filtered = filter_sales(
        ventas,
        (pd.Timestamp(start), pd.Timestamp(end)),
        selected_brands,
        selected_vendors,
        selected_weeks,
    )
    st.sidebar.caption(f"Registros filtrados: {len(filtered):,}")
    return filtered


def build_clientes_page(ventas: pd.DataFrame) -> None:
    st.subheader("Clientes")
    clientes = ventas.groupby("CLIENT_NAME", as_index=False).agg(
        total_mxn=("TOTAL_MXN", "sum"),
        total_usd=("TOTAL_USD", "sum"),
        facturas=("SALE_ID", "nunique"),
        ultima_compra=("SALE_DATE", "max"),
        origen=("ORIGIN", "first"),
    )
    clientes = clientes.sort_values(by="total_mxn", ascending=False)

    col1, col2, col3 = st.columns(3)
    col1.metric("Clientes facturados MXN", f"{(clientes['total_mxn'] > 0).sum():,}")
    col2.metric("Clientes facturados USD", f"{(clientes['total_usd'] > 0).sum():,}")
    col3.metric("Clientes distintos", f"{clientes['CLIENT_NAME'].nunique():,}")

    st.dataframe(clientes, use_container_width=True)
    export_buttons(clientes, "clientes_facturacion")

    st.subheader("Gráficas por origen")
    origen_resumen = ventas.groupby("ORIGIN", as_index=False).agg(
        clientes=("CLIENT_ID", "nunique"),
        facturas=("SALE_ID", "nunique"),
        monto_mxn=("TOTAL_MXN", "sum"),
        monto_usd=("TOTAL_USD", "sum"),
    )
    fig_clientes = px.bar(origen_resumen, x="ORIGIN", y="clientes", title="# Clientes por origen")
    fig_facturas = px.bar(origen_resumen, x="ORIGIN", y="facturas", title="# Facturas por origen")
    fig_montos = px.bar(
        origen_resumen,
        x="ORIGIN",
        y=["monto_mxn", "monto_usd"],
        barmode="group",
        title="Monto por origen (MXN vs USD)",
    )
    st.plotly_chart(fig_clientes, use_container_width=True)
    st.plotly_chart(fig_facturas, use_container_width=True)
    st.plotly_chart(fig_montos, use_container_width=True)


def build_ventas_page(ventas: pd.DataFrame, bundle: DataBundle) -> None:
    st.subheader("Agentes de venta")
    ventas_agente = ventas.groupby("VENDOR_NAME", as_index=False).agg(
        total_mxn=("TOTAL_MXN", "sum"),
        ventas_diarias=("SALE_DATE", "nunique"),
        pedidos=("SALE_ID", "nunique"),
    )
    ventas_agente["venta_promedio_diaria"] = ventas_agente["total_mxn"] / ventas_agente["ventas_diarias"]
    ventas_agente = ventas_agente.sort_values(by="total_mxn", ascending=False)
    st.dataframe(ventas_agente, use_container_width=True)
    export_buttons(ventas_agente, "ventas_por_agente")

    fig_agentes = px.bar(
        ventas_agente,
        x="VENDOR_NAME",
        y="total_mxn",
        title="Facturación por agente (MXN)",
    )
    st.plotly_chart(fig_agentes, use_container_width=True)

    st.subheader("Serie de tiempo por agente")
    granularity = st.selectbox("Granularidad", ["Diario", "Semanal", "Mensual"])
    ventas_time = ventas.copy()
    if granularity == "Semanal":
        ventas_time["PERIOD"] = ventas_time["SALE_DATE"].dt.to_period("W").dt.start_time
    elif granularity == "Mensual":
        ventas_time["PERIOD"] = ventas_time["SALE_DATE"].dt.to_period("M").dt.start_time
    else:
        ventas_time["PERIOD"] = ventas_time["SALE_DATE"].dt.date

    trend = (
        ventas_time.groupby(["PERIOD", "VENDOR_NAME"], as_index=False)["TOTAL_MXN"].sum()
    )
    fig_trend = px.line(trend, x="PERIOD", y="TOTAL_MXN", color="VENDOR_NAME", title="Tendencia por agente")
    st.plotly_chart(fig_trend, use_container_width=True)

    pedidos = bundle.pedidos.copy()
    pedidos_pendientes = pedidos[pedidos["STATUS"].isin(["PENDIENTE", "PARCIAL"])].shape[0]
    pedidos_total = pedidos["PEDIDO_ID"].nunique()
    tendencia_pedidos = ventas.groupby("SALE_DATE")["SALE_ID"].nunique().mean()

    col1, col2, col3 = st.columns(3)
    col1.metric("Facturación total", f"$ {ventas['TOTAL_MXN'].sum():,.2f}")
    col2.metric("Tendencia de venta (prom. pedidos)", f"{tendencia_pedidos:,.1f}")
    col3.metric("Pedidos por surtir", f"{pedidos_pendientes:,} / {pedidos_total:,}")


def build_productos_page(ventas: pd.DataFrame, bundle: DataBundle) -> None:
    st.subheader("Productos")
    productos = bundle.productos.copy()
    ventas_prod = ventas.groupby("PRODUCT_ID", as_index=False).agg(
        unidades_vendidas=("QUANTITY", "sum"),
        ventas_mxn=("TOTAL_MXN", "sum"),
    )
    productos = productos.merge(ventas_prod, on="PRODUCT_ID", how="left").fillna(0)
    productos["stock_value_mxn"] = productos["STOCK_UNITS"] * productos["BASE_PRICE"]
    productos["rotacion"] = productos["unidades_vendidas"] / productos["STOCK_UNITS"].replace(0, 1)

    col1, col2 = st.columns(2)
    col1.metric("Rotación de inventario", f"{productos['rotacion'].mean():.2f}")
    col2.metric("Valor de inventario", f"$ {productos['stock_value_mxn'].sum():,.2f}")

    productos_sorted = productos.sort_values(by="ventas_mxn", ascending=False)
    pareto = productos_sorted.head(10)
    st.subheader("Pareto Top 10 productos más vendidos")
    st.dataframe(
        pareto[["PRODUCT_NAME", "unidades_vendidas", "ventas_mxn", "STOCK_UNITS"]],
        use_container_width=True,
    )

    st.subheader("Stock ordenado por ventas mensuales")
    ventas_mes = ventas.copy()
    ventas_mes["MONTH"] = ventas_mes["SALE_DATE"].dt.to_period("M").dt.start_time
    ventas_mensuales = ventas_mes.groupby("PRODUCT_ID", as_index=False).agg(
        ventas_mensuales_mxn=("TOTAL_MXN", "sum"),
        unidades_mensuales=("QUANTITY", "sum"),
    )
    stock_tabla = productos.merge(ventas_mensuales, on="PRODUCT_ID", how="left").fillna(0)
    stock_tabla = stock_tabla.sort_values(by="ventas_mensuales_mxn", ascending=False)
    st.dataframe(
        stock_tabla[[
            "PRODUCT_NAME",
            "ventas_mensuales_mxn",
            "unidades_mensuales",
            "STOCK_UNITS",
            "stock_value_mxn",
        ]],
        use_container_width=True,
    )
    export_buttons(stock_tabla, "stock_productos")

    st.subheader("Tabla de rotación por producto")
    st.dataframe(
        productos_sorted[["PRODUCT_NAME", "rotacion", "unidades_vendidas", "ventas_mxn"]],
        use_container_width=True,
    )


def main() -> None:
    st.set_page_config(page_title="Dashboard SAI Alpha", page_icon="📊", layout="wide")
    ventas = load_sales()
    if ventas.empty:
        st.error("No hay datos disponibles. Ejecuta generate_mock_dbf.py para crear DBF.")
        return

    filtered = sidebar_filters(ventas)
    bundle = load_data()

    st.title("Dashboard Ejecutivo y Operativo para SAI Alpha")
    st.caption("Demo local con DBF, pandas y Streamlit")

    menu = st.sidebar.radio("Navegación", ["Ventas", "Clientes", "Productos"])

    if menu == "Ventas":
        build_ventas_page(filtered, bundle)
    elif menu == "Clientes":
        build_clientes_page(filtered)
    else:
        build_productos_page(filtered, bundle)


if __name__ == "__main__":
    main()
