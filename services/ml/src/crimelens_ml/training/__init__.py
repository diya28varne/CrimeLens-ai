"""Training orchestrators for CrimeLens risk + hotspot pipelines."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from crimelens_ml.evaluation import evaluate_classification, evaluate_clustering, evaluate_multiclass_auc
from crimelens_ml.explainability import explain_risk_model
from crimelens_ml.models import (
    build_risk_model,
    cluster_hotspots,
    fit_growth_classifier,
    fit_risk_model,
    predict_risk,
)
from crimelens_ml.preprocessing import encode_risk_label, temporal_split
from crimelens_ml.registry import save_model_bundle
from crimelens_ml.utils import load_yaml, ml_root, new_run_id, setup_logging, write_json
from crimelens_ml.utils.io import read_parquet, write_parquet


def _risk_frame(path: Path | None = None) -> pd.DataFrame:
    latest = path or (ml_root() / "datasets" / "engineered" / "risk_intelligence" / "latest.parquet")
    if not latest.exists():
        from crimelens_ml.synthetic import materialize_synthetic

        materialize_synthetic()
    return read_parquet(ml_root() / "datasets" / "engineered" / "risk_intelligence" / "latest.parquet")


def train_risk_pipeline(config_path: Path | None = None) -> dict[str, Any]:
    setup_logging()
    cfg = load_yaml(config_path or ml_root() / "configs" / "risk_xgboost.yaml")
    run_id = new_run_id("risk")
    df = _risk_frame()
    feature_cols = [c for c in cfg["features"] if c in df.columns]
    train_df, val_df, test_df = temporal_split(
        df,
        train_ratio=float(cfg["split"]["train_ratio"]),
        val_ratio=float(cfg["split"]["val_ratio"]),
    )

    model = build_risk_model(cfg)
    model = fit_risk_model(
        model,
        train_df[feature_cols],
        train_df["risk_level"],
        balanced=cfg.get("class_weight") == "balanced",
    )

    y_pred, conf = predict_risk(model, test_df[feature_cols])
    metrics = evaluate_classification(test_df["risk_level"], y_pred, cfg["label_order"])
    proba = model.predict_proba(test_df[feature_cols])
    metrics["auc"] = evaluate_multiclass_auc(encode_risk_label(test_df["risk_level"]).astype(int).to_numpy(), proba)

    # Validation snapshot
    val_pred, _ = predict_risk(model, val_df[feature_cols])
    val_metrics = evaluate_classification(val_df["risk_level"], val_pred, cfg["label_order"])

    bundle = save_model_bundle(
        cfg["model_code"],
        model,
        {
            "run_id": run_id,
            "feature_cols": feature_cols,
            "feature_set_id": cfg.get("feature_set_id"),
            "label_order": cfg["label_order"],
            "test_metrics": {k: v for k, v in metrics.items() if k != "report"},
            "val_macro_f1": val_metrics["macro_f1"],
            "n_train": len(train_df),
            "n_val": len(val_df),
            "n_test": len(test_df),
            "serves": ["/prediction", "/simulation", "/advisor", "/explain"],
        },
        version=run_id,
    )

    # Score sample for serving-shaped output
    scored = test_df[["district_code", "station_code", "grid_cell_id", "as_of_ts", "geohash"]].copy()
    scored["risk_level_pred"] = y_pred
    scored["confidence"] = conf
    scored["model_code"] = cfg["model_code"]
    scored["model_version"] = bundle["version"]
    score_path = write_parquet(scored, ml_root() / "datasets" / "processed" / f"risk_scores_{run_id}.parquet")

    # SHAP audit sample (D7)
    shap_payload = explain_risk_model(model, test_df[feature_cols], max_rows=48)
    shap_path = ml_root() / "artifacts" / cfg["model_code"] / bundle["version"] / "shap_audit.json"
    write_json(shap_path, shap_payload)

    report = {
        "run_id": run_id,
        "model": bundle,
        "metrics": {k: v for k, v in metrics.items() if k != "report"},
        "classification_report": metrics["report"],
        "score_path": str(score_path),
        "shap_path": str(shap_path),
        "top_global_features": shap_payload["global_importance"][:10],
    }
    report_path = ml_root() / "reports" / f"risk_{run_id}.json"
    write_json(report_path, report)
    md = ml_root() / "reports" / f"risk_{run_id}.md"
    md.write_text(
        "\n".join(
            [
                f"# CrimeLens Risk Model Report — `{run_id}`",
                "",
                f"- Model: `{cfg['model_code']}` (XGBoost)",
                f"- Feature set: `{cfg.get('feature_set_id')}`",
                f"- Train/Val/Test: {len(train_df)}/{len(val_df)}/{len(test_df)}",
                f"- Macro F1: **{metrics['macro_f1']:.3f}**",
                f"- Weighted F1: **{metrics['weighted_f1']:.3f}**",
                f"- ROC-AUC (OVR weighted): **{metrics['auc']['roc_auc_ovr_weighted']}**",
                "",
                "## Why these metrics",
                "- Macro F1 balances Critical/High with Low volume classes.",
                "- Critical recall is operationally costly to miss.",
                "- ROC-AUC supports map ranking independent of threshold.",
                "",
                "## Classification report",
                "```",
                metrics["report"],
                "```",
                "",
                "## Top SHAP features",
                *[f"- `{r['feature']}`: {r['importance']:.4f}" for r in shap_payload["global_importance"][:8]],
                "",
                "## Platform sinks",
                "- Scores → `/prediction` (`prediction_values`)",
                "- SHAP → `/explain` Decision Cards (`explanation_artifacts`)",
                "- Risk bands → `/simulation` twin overlays + `/advisor` evidence",
            ]
        ),
        encoding="utf-8",
    )
    report["report_md"] = str(md)
    return report


def train_hotspot_pipeline(config_path: Path | None = None) -> dict[str, Any]:
    setup_logging()
    cfg = load_yaml(config_path or ml_root() / "configs" / "hotspot_hdbscan.yaml")
    run_id = new_run_id("hotspot")
    path = ml_root() / "datasets" / "engineered" / "hotspot_evolution" / "latest.parquet"
    if not path.exists():
        from crimelens_ml.synthetic import materialize_synthetic

        materialize_synthetic()
    df = read_parquet(path)

    clustered, algorithm = cluster_hotspots(df, cfg)
    coords = clustered[["centroid_lat", "centroid_lon"]].to_numpy()
    cluster_metrics = evaluate_clustering(coords, clustered["cluster_id"].to_numpy())

    feature_cols = [c for c in cfg["features"] if c in clustered.columns]
    growth_model = fit_growth_classifier(clustered, feature_cols, cfg)
    growth_pred = growth_model.predict(clustered[feature_cols].fillna(0))
    growth_metrics = evaluate_classification(
        clustered["hotspot_growth"], growth_pred, cfg["growth_labels"]
    )

    bundle = save_model_bundle(
        cfg["model_code"],
        {"growth_model": growth_model, "algorithm": algorithm, "feature_cols": feature_cols},
        {
            "run_id": run_id,
            "cluster_algorithm": algorithm,
            "cluster_metrics": cluster_metrics,
            "growth_macro_f1": growth_metrics["macro_f1"],
            "serves": ["/map", "/simulation", "/advisor"],
        },
        version=run_id,
    )

    out = clustered.copy()
    out["hotspot_growth_pred"] = growth_pred
    out["cluster_algorithm"] = algorithm
    out_path = write_parquet(out, ml_root() / "datasets" / "processed" / f"hotspots_{run_id}.parquet")

    report = {
        "run_id": run_id,
        "algorithm": algorithm,
        "cluster_metrics": cluster_metrics,
        "growth_metrics": {k: v for k, v in growth_metrics.items() if k != "report"},
        "artifact": bundle,
        "output": str(out_path),
    }
    write_json(ml_root() / "reports" / f"hotspot_{run_id}.json", report)
    (ml_root() / "reports" / f"hotspot_{run_id}.md").write_text(
        "\n".join(
            [
                f"# CrimeLens Hotspot Report — `{run_id}`",
                "",
                f"- Clustering: **{algorithm}** (HDBSCAN preferred, DBSCAN fallback)",
                f"- Clusters: {cluster_metrics.get('n_clusters')}",
                f"- Silhouette: {cluster_metrics.get('silhouette')}",
                f"- Davies-Bouldin: {cluster_metrics.get('davies_bouldin')}",
                f"- Growth macro F1: **{growth_metrics['macro_f1']:.3f}**",
                "",
                "## Platform sinks",
                "- `hotspot_runs` / `hotspot_features` → Map + Digital Twin",
                "- Growth labels → Simulation overlays + Advisor risk areas",
            ]
        ),
        encoding="utf-8",
    )
    return report


from crimelens_ml.training.advisor import train_advisor_pipeline  # noqa: E402

__all__ = ["train_risk_pipeline", "train_hotspot_pipeline", "train_advisor_pipeline"]
