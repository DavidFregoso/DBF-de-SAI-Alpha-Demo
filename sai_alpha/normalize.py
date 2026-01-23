from __future__ import annotations

from collections.abc import Iterable

import pandas as pd


def normalize_cols(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    normalized = []
    for column in df.columns:
        cleaned = str(column).strip().upper().replace("-", "_").replace(" ", "_")
        while "__" in cleaned:
            cleaned = cleaned.replace("__", "_")
        normalized.append(cleaned)
    df.columns = normalized
    return df


def apply_aliases(df: pd.DataFrame, alias_map: dict[str, Iterable[str]]) -> pd.DataFrame:
    rename_map: dict[str, str] = {}
    for canonical, candidates in alias_map.items():
        for candidate in candidates:
            if candidate in df.columns:
                rename_map[candidate] = canonical
                break
    if rename_map:
        df = df.rename(columns=rename_map)
    return df


def coalesce_columns(
    df: pd.DataFrame,
    target: str,
    candidates: Iterable[str],
    drop_candidates: bool = False,
) -> pd.DataFrame:
    df = df.copy()
    if target not in df.columns:
        df[target] = pd.NA
    for candidate in candidates:
        if candidate in df.columns:
            df[target] = df[target].where(df[target].notna(), df[candidate])
    if drop_candidates:
        for candidate in candidates:
            if candidate != target and candidate in df.columns:
                df = df.drop(columns=candidate)
    return df


def ensure_columns(df: pd.DataFrame, defaults: dict[str, object]) -> pd.DataFrame:
    df = df.copy()
    for column, default in defaults.items():
        if column not in df.columns:
            df[column] = default
    return df


def ensure_metric(
    df: pd.DataFrame,
    metric_name: str,
    candidates: Iterable[str],
    default: float | int = 0,
) -> pd.DataFrame:
    df = df.copy()
    if metric_name not in df.columns:
        df[metric_name] = pd.NA
    for candidate in candidates:
        if candidate in df.columns:
            df[metric_name] = df[metric_name].where(df[metric_name].notna(), df[candidate])
    df[metric_name] = pd.to_numeric(df[metric_name], errors="coerce").fillna(default)
    return df
