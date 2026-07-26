"""Model wrappers — XGBoost risk + spatial clustering hotspot."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.utils.class_weight import compute_sample_weight
from xgboost import XGBClassifier

from crimelens_ml.preprocessing import RISK_LABELS, decode_risk_label, encode_risk_label


def build_risk_model(cfg: dict[str, Any]) -> XGBClassifier:
    p = cfg.get("xgboost", {})
    return XGBClassifier(
        n_estimators=int(p.get("n_estimators", 120)),
        max_depth=int(p.get("max_depth", 5)),
        learning_rate=float(p.get("learning_rate", 0.08)),
        subsample=float(p.get("subsample", 0.9)),
        colsample_bytree=float(p.get("colsample_bytree", 0.85)),
        objective=p.get("objective", "multi:softprob"),
        eval_metric=p.get("eval_metric", "mlogloss"),
        num_class=int(p.get("num_class", 4)),
        random_state=42,
        n_jobs=2,
    )


def fit_risk_model(
    model: XGBClassifier,
    X: pd.DataFrame,
    y: pd.Series,
    balanced: bool = True,
) -> XGBClassifier:
    y_enc = encode_risk_label(y).astype(int)
    sw = compute_sample_weight("balanced", y_enc) if balanced else None
    model.fit(X, y_enc, sample_weight=sw)
    return model


def predict_risk(model: XGBClassifier, X: pd.DataFrame) -> tuple[list[str], np.ndarray]:
    proba = model.predict_proba(X)
    codes = np.argmax(proba, axis=1)
    conf = proba.max(axis=1)
    return decode_risk_label(codes), conf


def cluster_hotspots(
    df: pd.DataFrame,
    cfg: dict[str, Any],
) -> tuple[pd.DataFrame, str]:
    """HDBSCAN if installed, else DBSCAN fallback — both CrimeLens-configured."""
    spatial = cfg.get("spatial", {})
    coords = df[["centroid_lat", "centroid_lon"]].to_numpy()
    algorithm = "dbscan"
    labels: np.ndarray

    try:
        import hdbscan  # type: ignore

        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=int(spatial.get("min_cluster_size", 8)),
            min_samples=int(spatial.get("min_samples", 4)),
        )
        labels = clusterer.fit_predict(coords)
        algorithm = "hdbscan"
    except Exception:
        clusterer = DBSCAN(
            eps=float(spatial.get("dbscan_eps", 0.035)),
            min_samples=int(spatial.get("dbscan_min_samples", 5)),
        )
        labels = clusterer.fit_predict(coords)
        algorithm = "dbscan"

    out = df.copy()
    out["cluster_id"] = labels
    out["is_hotspot_core"] = (out["cluster_id"] >= 0).astype(int)
    return out, algorithm


def fit_growth_classifier(df: pd.DataFrame, feature_cols: list[str], cfg: dict[str, Any]) -> GradientBoostingClassifier:
    g = cfg.get("growth_classifier", {})
    model = GradientBoostingClassifier(
        n_estimators=int(g.get("n_estimators", 80)),
        max_depth=int(g.get("max_depth", 3)),
        random_state=42,
    )
    X = df[feature_cols].fillna(0)
    y = df["hotspot_growth"]
    model.fit(X, y)
    return model


__all__ = [
    "RISK_LABELS",
    "build_risk_model",
    "fit_risk_model",
    "predict_risk",
    "cluster_hotspots",
    "fit_growth_classifier",
]
