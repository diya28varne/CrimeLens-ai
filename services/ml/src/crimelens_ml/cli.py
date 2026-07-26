"""CrimeLens ML CLI — offline plane entrypoint."""

from __future__ import annotations

import argparse
import json

from crimelens_ml.utils import ensure_dirs, setup_logging


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    ensure_dirs()
    parser = argparse.ArgumentParser(prog="crimelens-ml", description="CrimeLens AI offline ML plane")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_synth = sub.add_parser("synthesize", help="Generate domain-inspired synthetic CrimeLens world")
    p_synth.add_argument("--cells", type=int, default=480)
    p_synth.add_argument("--days", type=int, default=45)
    p_synth.add_argument("--seed", type=int, default=42)

    sub.add_parser("train-risk", help="Train XGBoost crime risk model (D1)")
    sub.add_parser("train-hotspot", help="Run hotspot clustering + growth model (D2)")
    sub.add_parser("train-advisor", help="Train Advisor action ranker (D3)")
    sub.add_parser("build-mart", help="Build executive intelligence mart (D5)")
    p_opt = sub.add_parser("optimize-resources", help="Patrol zone/shift optimization (D6)")
    p_opt.add_argument("--officers", type=int, default=18)
    p_opt.add_argument("--vehicles", type=int, default=6)
    sub.add_parser("promote", help="Build artifact promotion bundle for API ingest")
    sub.add_parser("extract-status", help="Show PostGIS extract readiness")
    sub.add_parser("run-phase-ab", help="Synthesize + train risk + train hotspot")
    sub.add_parser("run-phase-c", help="Advisor + executive mart + resources + promote")

    args = parser.parse_args(argv)

    if args.cmd == "synthesize":
        from crimelens_ml.synthetic import materialize_synthetic

        print(json.dumps(materialize_synthetic(n_cells=args.cells, n_days=args.days, seed=args.seed), indent=2))
        return 0

    if args.cmd == "train-risk":
        from crimelens_ml.training import train_risk_pipeline

        print(json.dumps(train_risk_pipeline(), indent=2, default=str))
        return 0

    if args.cmd == "train-hotspot":
        from crimelens_ml.training import train_hotspot_pipeline

        print(json.dumps(train_hotspot_pipeline(), indent=2, default=str))
        return 0

    if args.cmd == "train-advisor":
        from crimelens_ml.training import train_advisor_pipeline

        print(json.dumps(train_advisor_pipeline(), indent=2, default=str))
        return 0

    if args.cmd == "build-mart":
        from crimelens_ml.datasets_builders.executive import build_executive_mart

        print(json.dumps(build_executive_mart(), indent=2, default=str))
        return 0

    if args.cmd == "optimize-resources":
        from crimelens_ml.optimization import optimize_resources

        print(json.dumps(optimize_resources(officers=args.officers, vehicles=args.vehicles), indent=2, default=str))
        return 0

    if args.cmd == "promote":
        from crimelens_ml.registry.promote import build_promotion_bundle

        print(json.dumps(build_promotion_bundle(), indent=2))
        return 0

    if args.cmd == "extract-status":
        from crimelens_ml.data.extract import extract_status

        print(json.dumps(extract_status(), indent=2))
        return 0

    if args.cmd == "run-phase-ab":
        from crimelens_ml.synthetic import materialize_synthetic
        from crimelens_ml.training import train_hotspot_pipeline, train_risk_pipeline

        synth = materialize_synthetic()
        risk = train_risk_pipeline()
        hotspot = train_hotspot_pipeline()
        print(
            json.dumps(
                {
                    "synthetic": synth,
                    "risk_run": risk.get("run_id"),
                    "risk_macro_f1": risk.get("metrics", {}).get("macro_f1"),
                    "hotspot_run": hotspot.get("run_id"),
                    "hotspot_algorithm": hotspot.get("algorithm"),
                    "hotspot_growth_macro_f1": hotspot.get("growth_metrics", {}).get("macro_f1"),
                },
                indent=2,
            )
        )
        return 0

    if args.cmd == "run-phase-c":
        from crimelens_ml.datasets_builders.advisor import materialize_advisor_dataset
        from crimelens_ml.datasets_builders.executive import build_executive_mart
        from crimelens_ml.optimization import optimize_resources
        from crimelens_ml.registry.promote import build_promotion_bundle
        from crimelens_ml.training import train_advisor_pipeline

        # Ensure A/B artifacts exist
        risk_latest = __import__("pathlib").Path(__import__("crimelens_ml.utils", fromlist=["ml_root"]).ml_root() / "datasets" / "engineered" / "risk_intelligence" / "latest.parquet")
        if not risk_latest.exists():
            from crimelens_ml.synthetic import materialize_synthetic
            from crimelens_ml.training import train_hotspot_pipeline, train_risk_pipeline

            materialize_synthetic()
            train_risk_pipeline()
            train_hotspot_pipeline()

        advisor_data = materialize_advisor_dataset()
        advisor = train_advisor_pipeline()
        mart = build_executive_mart()
        resources = optimize_resources()
        promotion = build_promotion_bundle()
        print(
            json.dumps(
                {
                    "advisor_data_rows": advisor_data.get("n_rows"),
                    "advisor_run": advisor.get("run_id"),
                    "advisor_algorithm": advisor.get("algorithm"),
                    "advisor_macro_f1": advisor.get("metrics", {}).get("macro_f1"),
                    "advisor_top3": advisor.get("top3_accuracy"),
                    "executive_mart_rows": mart.get("n_rows"),
                    "context_packs": mart.get("n_context_packs"),
                    "resource_solver": resources.get("solver"),
                    "resource_assignments": len(resources.get("assignments", [])),
                    "promotion": promotion,
                },
                indent=2,
                default=str,
            )
        )
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
