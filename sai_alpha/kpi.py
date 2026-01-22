from __future__ import annotations

import pandas as pd


def resumen_kpis(ventas: pd.DataFrame) -> dict[str, float | int | str]:
    revenue_col = "REVENUE_MXN" if "REVENUE_MXN" in ventas.columns else "AMOUNT_MXN"
    qty_col = "QTY" if "QTY" in ventas.columns else "QUANTITY"
    total_revenue = float(ventas[revenue_col].sum()) if revenue_col in ventas.columns else 0.0
    total_units = int(ventas[qty_col].sum()) if qty_col in ventas.columns else 0
    avg_ticket = (
        float(ventas.groupby("SALE_ID")[revenue_col].sum().mean())
        if not ventas.empty and revenue_col in ventas.columns
        else 0.0
    )
    top_brand = (
        ventas.groupby("BRAND")[revenue_col].sum().sort_values(ascending=False).index[0]
        if not ventas.empty and revenue_col in ventas.columns
        else "N/A"
    )
    return {
        "total_revenue": total_revenue,
        "total_units": total_units,
        "avg_ticket": avg_ticket,
        "top_brand": top_brand,
    }


def kpis_by_dimension(ventas: pd.DataFrame, dimension: str) -> pd.DataFrame:
    revenue_col = "REVENUE_MXN" if "REVENUE_MXN" in ventas.columns else "AMOUNT_MXN"
    qty_col = "QTY" if "QTY" in ventas.columns else "QUANTITY"
    grouped = (
        ventas.groupby(dimension)
        .agg(
            revenue=(revenue_col, "sum"),
            units=(qty_col, "sum"),
            avg_ticket=(revenue_col, "mean"),
            orders=("FACTURA_ID" if "FACTURA_ID" in ventas.columns else "SALE_ID", "nunique"),
        )
        .reset_index()
    )
    return grouped.sort_values(by="revenue", ascending=False)
