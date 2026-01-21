from __future__ import annotations

import pandas as pd


def resumen_kpis(ventas: pd.DataFrame) -> dict[str, float | int | str]:
    total_revenue = float(ventas["REVENUE"].sum())
    total_units = int(ventas["QUANTITY"].sum())
    avg_ticket = float(ventas.groupby("SALE_ID")["REVENUE"].sum().mean()) if not ventas.empty else 0.0
    top_brand = (
        ventas.groupby("BRAND")["REVENUE"].sum().sort_values(ascending=False).index[0]
        if not ventas.empty
        else "N/A"
    )
    return {
        "total_revenue": total_revenue,
        "total_units": total_units,
        "avg_ticket": avg_ticket,
        "top_brand": top_brand,
    }


def kpis_by_dimension(ventas: pd.DataFrame, dimension: str) -> pd.DataFrame:
    grouped = (
        ventas.groupby(dimension)
        .agg(
            revenue=("REVENUE", "sum"),
            units=("QUANTITY", "sum"),
            avg_ticket=("REVENUE", "mean"),
            orders=("SALE_ID", "nunique"),
        )
        .reset_index()
    )
    return grouped.sort_values(by="revenue", ascending=False)
