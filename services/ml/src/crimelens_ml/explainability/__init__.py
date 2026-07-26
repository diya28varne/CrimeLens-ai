"""Explainability for CrimeLens Decision Cards / audit dataset D7.

Uses XGBoost native `pred_contribs` (SHAP-style additive attributions) by default
so the plane stays installable on Python 3.12 Windows without llvmlite.
Optional `shap` extra can be enabled later for TreeExplainer parity.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from xgboost import XGBClassifier

from crimelens_ml.feature_engineering import FEATURE_CATALOG


def explain_risk_model(
    model: XGBClassifier,
    X: pd.DataFrame,
    max_rows: int = 64,
) -> dict[str, Any]:
    sample = X.iloc[: max(1, min(max_rows, len(X)))].copy()
    # Try optional shap package; fall back to XGBoost contribs
    try:
        return _explain_with_shap(model, sample)
    except Exception:
        return _explain_with_xgboost_contribs(model, sample)


def _explain_with_shap(model: XGBClassifier, sample: pd.DataFrame) -> dict[str, Any]:
    import shap  # type: ignore

    explainer = shap.TreeExplainer(model)
    values = explainer.shap_values(sample)
    if isinstance(values, list):
        abs_mean = np.mean([np.abs(v) for v in values], axis=0)
        local = values
    else:
        abs_mean = np.abs(values)
        local = [values]
    return _pack(model, sample, abs_mean, local, method="shap.TreeExplainer")


def _explain_with_xgboost_contribs(model: XGBClassifier, sample: pd.DataFrame) -> dict[str, Any]:
    booster = model.get_booster()
    # contribs shape: (n_rows, n_classes * (n_features + 1)) for multi:softprob in recent xgb
    dm = sample
    contribs = model.predict(dm, output_margin=False)  # ensure fitted
    raw = booster.predict(data=_to_dmatrix(sample), pred_contribs=True)
    raw = np.asarray(raw)

    n_features = sample.shape[1]
    if raw.ndim == 2 and raw.shape[1] == n_features + 1:
        # binary-style / single output
        local_vals = raw[:, :-1]
        abs_mean = np.abs(local_vals)
        local = [local_vals]
    elif raw.ndim == 2 and raw.shape[1] % (n_features + 1) == 0:
        n_classes = raw.shape[1] // (n_features + 1)
        chunks = []
        for c in range(n_classes):
            start = c * (n_features + 1)
            end = start + n_features
            chunks.append(raw[:, start:end])
        abs_mean = np.mean([np.abs(c) for c in chunks], axis=0)
        local = chunks
    elif raw.ndim == 3:
        # (n_rows, n_classes, n_features+1)
        chunks = [raw[:, c, :-1] for c in range(raw.shape[1])]
        abs_mean = np.mean([np.abs(c) for c in chunks], axis=0)
        local = chunks
    else:
        # Fallback: feature importances only
        gain = model.feature_importances_
        abs_mean = np.tile(gain, (len(sample), 1))
        local = [abs_mean]

    _ = contribs  # keep predict path warm
    return _pack(model, sample, abs_mean, local, method="xgboost.pred_contribs")


def _to_dmatrix(sample: pd.DataFrame):
    import xgboost as xgb

    return xgb.DMatrix(sample, feature_names=list(sample.columns))


def _pack(
    model: XGBClassifier,
    sample: pd.DataFrame,
    abs_mean: np.ndarray,
    local: list[np.ndarray],
    method: str,
) -> dict[str, Any]:
    global_importance = (
        pd.DataFrame({"feature": sample.columns, "importance": np.asarray(abs_mean).mean(axis=0)})
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )
    pred = model.predict(sample)
    proba = model.predict_proba(sample)
    rows = []
    for i in range(len(sample)):
        cls = int(pred[i])
        shap_row = local[min(cls, len(local) - 1)][i]
        contrib = (
            pd.DataFrame(
                {
                    "feature": sample.columns,
                    "contribution": shap_row,
                    "value": sample.iloc[i].to_numpy(),
                }
            )
            .assign(abs_c=lambda d: d["contribution"].abs())
            .sort_values("abs_c", ascending=False)
            .head(8)
        )
        top = contrib.drop(columns=["abs_c"]).to_dict(orient="records")
        rows.append(
            {
                "row_index": int(i),
                "predicted_class": cls,
                "confidence": float(proba[i].max()),
                "top_features": top,
                "nl_explanation": _nl_explanation(top, float(proba[i].max())),
            }
        )

    return {
        "method": method,
        "global_importance": global_importance.to_dict(orient="records"),
        "local_explanations": rows,
        "feature_catalog_slice": {
            f: FEATURE_CATALOG[f]
            for f in global_importance["feature"].head(12)
            if f in FEATURE_CATALOG
        },
    }


def _nl_explanation(top: list[dict[str, Any]], confidence: float) -> str:
    if not top:
        return f"Model confidence {confidence:.0%} with no dominant features."
    drivers = []
    for t in top[:3]:
        direction = "increased" if float(t["contribution"]) > 0 else "decreased"
        drivers.append(f"{t['feature']} {direction} risk")
    return (
        f"Prediction confidence {confidence:.0%}. Primary drivers: "
        + "; ".join(drivers)
        + ". Factors are model attributions, not proof of causation."
    )
