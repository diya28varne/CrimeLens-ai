"""Backward-compatible re-export — prefer crimelens_ml.feature_engineering. """

from crimelens_ml.feature_engineering import FEATURE_CATALOG, derive_risk_labels, engineer_risk_features

__all__ = ["FEATURE_CATALOG", "derive_risk_labels", "engineer_risk_features"]
