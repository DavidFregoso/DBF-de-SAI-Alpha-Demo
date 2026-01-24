from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from sai_alpha.formatting import plotly_hover_money
from sai_alpha.ui import build_time_series


def _safe_df(df: pd.DataFrame) -> pd.DataFrame:
    return df.copy() if df is not None else pd.DataFrame()


def revenue_trend(
    df: pd.DataFrame,
    date_col: str,
    revenue_col: str,
    currency: str,
    granularity: str,
    theme_cfg: dict[str, Any],
) -> go.Figure:
    series = build_time_series(df, date_col, revenue_col, granularity)
    fig = px.line(
        series,
        x=date_col,
        y=revenue_col,
        markers=True,
        labels={date_col: "Periodo", revenue_col: f"Ventas ({currency})"},
    )
    fig.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
    fig.update_traces(hovertemplate=f"%{{x|%d/%m/%Y}}<br>{plotly_hover_money(currency)}")
    fig.update_yaxes(tickformat=",.2f")
    return fig


def orders_and_revenue_trend(
    df: pd.DataFrame,
    date_col: str,
    revenue_col: str,
    order_col: str,
    currency: str,
    granularity: str,
    theme_cfg: dict[str, Any],
) -> go.Figure:
    series_rev = build_time_series(df, date_col, revenue_col, granularity)
    working = df.copy()
    if order_col not in working.columns:
        working[order_col] = range(1, len(working) + 1)
    series_orders = (
        working.groupby(pd.Grouper(key=date_col, freq=_granularity_freq(granularity)))[order_col]
        .nunique()
        .reset_index(name="orders")
    )
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=series_rev[date_col],
            y=series_rev[revenue_col],
            mode="lines+markers",
            name=f"Ventas ({currency})",
            hovertemplate=f"%{{x|%d/%m/%Y}}<br>{plotly_hover_money(currency)}",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=series_orders[date_col],
            y=series_orders["orders"],
            mode="lines+markers",
            name="Pedidos",
            yaxis="y2",
            hovertemplate="%{x|%d/%m/%Y}<br>Pedidos: %{y:,.0f}<extra></extra>",
        )
    )
    fig.update_layout(
        height=340,
        margin=dict(l=20, r=20, t=40, b=20),
        yaxis=dict(title=f"Ventas ({currency})", tickformat=",.2f"),
        yaxis2=dict(
            title="Pedidos",
            overlaying="y",
            side="right",
            tickformat=",.0f",
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def top_categories_bar(
    df: pd.DataFrame,
    category_col: str,
    revenue_col: str,
    currency: str,
    theme_cfg: dict[str, Any],
    top_n: int = 10,
) -> go.Figure:
    summary = (
        _safe_df(df)
        .groupby(category_col, dropna=False)[revenue_col]
        .sum()
        .reset_index()
        .sort_values(revenue_col, ascending=False)
        .head(top_n)
    )
    fig = px.bar(
        summary,
        x=revenue_col,
        y=category_col,
        orientation="h",
        labels={revenue_col: f"Ventas ({currency})", category_col: "Categoría"},
    )
    fig.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
    fig.update_traces(hovertemplate=f"%{{y}}<br>{plotly_hover_money(currency)}")
    fig.update_xaxes(tickformat=",.2f")
    return fig


def channel_share_donut(
    df: pd.DataFrame,
    channel_col: str,
    revenue_col: str,
    currency: str,
    theme_cfg: dict[str, Any],
) -> go.Figure:
    summary = (
        _safe_df(df)
        .groupby(channel_col, dropna=False)[revenue_col]
        .sum()
        .reset_index()
        .sort_values(revenue_col, ascending=False)
    )
    fig = px.pie(
        summary,
        values=revenue_col,
        names=channel_col,
        hole=0.45,
    )
    fig.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
    fig.update_traces(hovertemplate=f"%{{label}}<br>{plotly_hover_money(currency)}")
    return fig


def weekday_heatmap(
    df: pd.DataFrame,
    date_col: str,
    revenue_col: str,
    currency: str,
    theme_cfg: dict[str, Any],
) -> go.Figure | None:
    sales = _safe_df(df)
    if sales.empty or date_col not in sales.columns:
        return None
    working = sales[[date_col, revenue_col]].copy()
    working = working.dropna()
    if working.empty:
        return None
    day_map = {
        0: "Lunes",
        1: "Martes",
        2: "Miércoles",
        3: "Jueves",
        4: "Viernes",
        5: "Sábado",
        6: "Domingo",
    }
    working["weekday"] = working[date_col].dt.dayofweek.map(day_map)
    working["week"] = working[date_col].dt.isocalendar().week.astype(int)
    pivot = working.pivot_table(index="weekday", columns="week", values=revenue_col, aggfunc="sum")
    if pivot.empty or pivot.shape[1] < 2:
        return None
    fig = px.imshow(
        pivot,
        aspect="auto",
        labels=dict(x="Semana ISO", y="Día", color=f"Ventas ({currency})"),
    )
    fig.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
    fig.update_traces(hovertemplate=f"Semana: %{{x}}<br>Día: %{{y}}<br>{plotly_hover_money(currency)}")
    return fig


def stacked_channel_over_time(
    df: pd.DataFrame,
    date_col: str,
    channel_col: str,
    revenue_col: str,
    currency: str,
    granularity: str,
    theme_cfg: dict[str, Any],
) -> go.Figure:
    grouped = (
        _safe_df(df)
        .groupby([pd.Grouper(key=date_col, freq=_granularity_freq(granularity)), channel_col])[revenue_col]
        .sum()
        .reset_index()
    )
    fig = px.bar(
        grouped,
        x=date_col,
        y=revenue_col,
        color=channel_col,
        labels={revenue_col: f"Ventas ({currency})", date_col: "Periodo"},
    )
    fig.update_layout(height=320, barmode="stack", margin=dict(l=20, r=20, t=40, b=20))
    fig.update_traces(hovertemplate=f"%{{x|%d/%m/%Y}}<br>{plotly_hover_money(currency)}")
    fig.update_yaxes(tickformat=",.2f")
    return fig


def invoice_type_donut(
    df: pd.DataFrame,
    invoice_col: str,
    revenue_col: str,
    currency: str,
    theme_cfg: dict[str, Any],
) -> go.Figure:
    summary = (
        _safe_df(df)
        .groupby(invoice_col, dropna=False)[revenue_col]
        .sum()
        .reset_index()
        .sort_values(revenue_col, ascending=False)
    )
    fig = px.pie(summary, values=revenue_col, names=invoice_col, hole=0.5)
    fig.update_layout(height=320, margin=dict(l=20, r=20, t=40, b=20))
    fig.update_traces(hovertemplate=f"%{{label}}<br>{plotly_hover_money(currency)}")
    return fig


def _granularity_freq(granularity: str) -> str:
    if granularity == "Diario":
        return "D"
    if granularity == "Semanal":
        return "W-MON"
    if granularity == "Mensual":
        return "ME"
    if granularity == "Anual":
        return "Y"
    return "W-MON"
