"""Evaluation metrics for CrimeLens ML tasks."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    calinski_harabasz_score,
    classification_report,
    davies_bouldin_score,
    f1_score,
    precision_recall_fscore_support,
    roc_auc_score,
    silhouette_score,
)


def evaluate_classification(y_true: list[str] | pd.Series, y_pred: list[str] | pd.Series, labels: list[str]) -> dict[str, Any]:
    yt = list(y_true)
    yp = list(y_pred)
    precision, recall, f1, support = precision_recall_fscore_support(
        yt, yp, labels=labels, zero_division=0
    )
    return {
        "macro_f1": float(f1_score(yt, yp, average="macro", zero_division=0)),
        "weighted_f1": float(f1_score(yt, yp, average="weighted", zero_division=0)),
        "per_class": {
            labels[i]: {
                "precision": float(precision[i]),
                "recall": float(recall[i]),
                "f1": float(f1[i]),
                "support": int(support[i]),
            }
            for i in range(len(labels))
        },
        "report": classification_report(yt, yp, labels=labels, zero_division=0),
        "why": {
            "macro_f1": "Treats Critical/High equally important despite imbalance",
            "weighted_f1": "Reflects operational volume mix",
            "per_class_recall_Critical": "Missed Critical cells are highest operational cost",
        },
    }


def evaluate_multiclass_auc(
    y_true_codes: np.ndarray,
    proba: np.ndarray,
) -> dict[str, float]:
    try:
        auc = float(roc_auc_score(y_true_codes, proba, multi_class="ovr", average="weighted"))
    except ValueError:
        auc = float("nan")
    return {
        "roc_auc_ovr_weighted": auc,
        "note": "Threshold-free ranking quality for map ordering",
    }


def evaluate_clustering(coords: np.ndarray, labels: np.ndarray) -> dict[str, Any]:
    mask = labels >= 0
    if mask.sum() < 5 or len(set(labels[mask])) < 2:
        return {
            "silhouette": None,
            "davies_bouldin": None,
            "calinski_harabasz": None,
            "n_clusters": int(len(set(labels)) - (1 if -1 in labels else 0)),
            "noise_points": int((labels < 0).sum()),
            "note": "Insufficient clustered points for internal metrics",
        }
    X = coords[mask]
    y = labels[mask]
    return {
        "silhouette": float(silhouette_score(X, y)),
        "davies_bouldin": float(davies_bouldin_score(X, y)),
        "calinski_harabasz": float(calinski_harabasz_score(X, y)),
        "n_clusters": int(len(set(y))),
        "noise_points": int((labels < 0).sum()),
        "why": {
            "silhouette": "Compactness/separation of hotspot cores",
            "davies_bouldin": "Lower is better cluster separation",
            "calinski_harabasz": "Higher is better variance ratio",
        },
    }
