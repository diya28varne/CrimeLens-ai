"""Preprocessing — missing values, outliers, encoding, spatial/temporal checks."""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd

from crimelens_ml.utils import load_common_config, validate_karnataka_coords


RISK_LABELS = ["Low", "Medium", "High", "Critical"]


def validate_coordinates(df: pd.DataFrame, lon_col: str = "centroid_lon", lat_col: str = "centroid_lat") -> pd.DataFrame:
    cfg = load_common_config()
    bbox = cfg["karnataka_bbox"]
    mask = df.apply(
        lambda r: validate_karnataka_coords(float(r[lon_col]), float(r[lat_col]), bbox),
        axis=1,
    )
    out = df.loc[mask].copy()
    out["coord_valid"] = True
    return out


def impute_numeric(df: pd.DataFrame, cols: Iterable[str], group_col: str | None = "district_code") -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c not in out.columns:
            continue
        if group_col and group_col in out.columns:
            out[c] = out.groupby(group_col)[c].transform(lambda s: s.fillna(s.median()))
        out[c] = out[c].fillna(out[c].median() if out[c].notna().any() else 0.0)
    return out


def winsorize(df: pd.DataFrame, cols: Iterable[str], lower: float = 0.01, upper: float = 0.99) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c not in out.columns:
            continue
        lo, hi = out[c].quantile(lower), out[c].quantile(upper)
        out[c] = out[c].clip(lo, hi)
    return out


def encode_risk_label(series: pd.Series) -> pd.Series:
    mapping = {k: i for i, k in enumerate(RISK_LABELS)}
    return series.map(mapping).astype("Int64")


def decode_risk_label(codes: np.ndarray | pd.Series) -> list[str]:
    return [RISK_LABELS[int(i)] for i in codes]


def add_cyclical_time(df: pd.DataFrame, hour_col: str = "hour") -> pd.DataFrame:
    out = df.copy()
    hours = out[hour_col].astype(float)
    out["hour_sin"] = np.sin(2 * np.pi * hours / 24.0)
    out["hour_cos"] = np.cos(2 * np.pi * hours / 24.0)
    return out


def temporal_split(
    df: pd.DataFrame,
    time_col: str = "as_of_ts",
    train_ratio: float = 0.7,
    val_ratio: float = 0.15,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    ordered = df.sort_values(time_col).reset_index(drop=True)
    n = len(ordered)
    i_train = int(n * train_ratio)
    i_val = int(n * (train_ratio + val_ratio))
    return ordered.iloc[:i_train], ordered.iloc[i_train:i_val], ordered.iloc[i_val:]
