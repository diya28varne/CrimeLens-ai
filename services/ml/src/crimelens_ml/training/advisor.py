"""Advisor action ranker training (LightGBM with sklearn HistGBM fallback)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.utils.class_weight import compute_sample_weight

from crimelens_ml.datasets_builders.advisor import ACTIONS, materialize_advisor_dataset
from crimelens_ml.evaluation import evaluate_classification
from crimelens_ml.preprocessing import temporal_split
from crimelens_ml.registry import save_model_bundle
from crimelens_ml.utils import load_yaml, ml_root, new_run_id, write_json
from crimelens_ml.utils.io import read_parquet, write_parquet


def _build_model(cfg: dict[str, Any]) -> tuple[Any, str]:
    try:
        import lightgbm as lgb

        p = cfg.get("lightgbm", {})
        model = lgb.LGBMClassifier(
            n_estimators=int(p.get("n_estimators", 150)),
            learning_rate=float(p.get("learning_rate", 0.07)),
            num_leaves=int(p.get("num_leaves", 31)),
            max_depth=int(p.get("max_depth", 6)),
            subsample=float(p.get("subsample", 0.9)),
            colsample_bytree=float(p.get("colsample_bytree", 0.85)),
            random_state=42,
            n_jobs=2,
        )
        return model, "lightgbm"
    except Exception:
        p = cfg.get("sklearn_fallback", {})
        model = HistGradientBoostingClassifier(
            max_iter=int(p.get("max_iter", 200)),
            learning_rate=float(p.get("learning_rate", 0.08)),
            max_depth=int(p.get("max_depth", 6)),
            random_state=42,
        )
        return model, "sklearn_hist_gradient_boosting"


def train_advisor_pipeline(config_path=None) -> dict[str, Any]:
    cfg = load_yaml(config_path or ml_root() / "configs" / "advisor_lightgbm.yaml")
    run_id = new_run_id("advisor")

    data_path = ml_root() / "datasets" / "engineered" / "strategic_intelligence" / "latest.parquet"
    if not data_path.exists():
        materialize_advisor_dataset()
    df = read_parquet(data_path)

    feature_cols = [c for c in cfg["features"] if c in df.columns]
    train_df, val_df, test_df = temporal_split(
        df,
        train_ratio=float(cfg["split"]["train_ratio"]),
        val_ratio=float(cfg["split"]["val_ratio"]),
    )

    le = LabelEncoder()
    le.fit(ACTIONS)
    y_train = le.transform(train_df["recommended_action"])
    y_test = le.transform(test_df["recommended_action"])

    model, algo = _build_model(cfg)
    sw = None
    if cfg.get("class_weight") == "balanced":
        sw = compute_sample_weight("balanced", y_train)

    if algo == "lightgbm":
        model.fit(train_df[feature_cols], y_train, sample_weight=sw)
    else:
        # HistGBM uses sample_weight
        model.fit(train_df[feature_cols], y_train, sample_weight=sw)

    pred_codes = model.predict(test_df[feature_cols])
    y_pred = le.inverse_transform(pred_codes.astype(int))
    metrics = evaluate_classification(test_df["recommended_action"], y_pred, ACTIONS)

    # Top-3 hit rate (map proba columns via model.classes_)
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(test_df[feature_cols])
        class_ids = list(getattr(model, "classes_", range(proba.shape[1])))
        top3 = 0
        for i, true_code in enumerate(y_test):
            top_idx = np.argsort(proba[i])[::-1][:3]
            top_classes = [class_ids[j] for j in top_idx]
            if true_code in top_classes:
                top3 += 1
        top3_acc = top3 / max(len(y_test), 1)
    else:
        top3_acc = float("nan")

    bundle = save_model_bundle(
        cfg["model_code"],
        {"model": model, "label_encoder_classes": list(le.classes_), "feature_cols": feature_cols, "algorithm": algo},
        {
            "run_id": run_id,
            "algorithm": algo,
            "feature_cols": feature_cols,
            "feature_set_id": cfg.get("feature_set_id"),
            "actions": ACTIONS,
            "test_macro_f1": metrics["macro_f1"],
            "top3_accuracy": top3_acc,
            "n_train": len(train_df),
            "n_test": len(test_df),
            "label_source": "policy_heuristic_v1",
            "serves": cfg.get("serves", ["/advisor"]),
        },
        version=run_id,
    )

    scored = test_df[["district_code", "station_code", "as_of_ts"]].copy()
    scored["recommended_action_pred"] = y_pred
    if hasattr(model, "predict_proba"):
        scored["confidence"] = model.predict_proba(test_df[feature_cols]).max(axis=1)
    score_path = write_parquet(scored, ml_root() / "datasets" / "processed" / f"advisor_scores_{run_id}.parquet")

    report = {
        "run_id": run_id,
        "algorithm": algo,
        "metrics": {k: v for k, v in metrics.items() if k != "report"},
        "top3_accuracy": top3_acc,
        "artifact": bundle,
        "score_path": str(score_path),
        "classification_report": metrics["report"],
    }
    write_json(ml_root() / "reports" / f"advisor_{run_id}.json", report)
    (ml_root() / "reports" / f"advisor_{run_id}.md").write_text(
        "\n".join(
            [
                f"# CrimeLens Advisor Ranker — `{run_id}`",
                "",
                f"- Algorithm: **{algo}** (LightGBM preferred)",
                f"- Macro F1: **{metrics['macro_f1']:.3f}**",
                f"- Top-3 accuracy: **{top3_acc:.3f}**",
                f"- Labels: policy heuristics (`policy_heuristic_v1`) — review before production promotion",
                "",
                "## Platform sinks",
                "- Action priors → `/advisor` ActionOut ranking",
                "- Summaries → `/reports` recommended_actions_json",
                "- Constraints respected in resource optimizer (D6)",
                "",
                "```",
                metrics["report"],
                "```",
            ]
        ),
        encoding="utf-8",
    )
    return report
