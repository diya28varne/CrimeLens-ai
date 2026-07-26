"""Backward-compatible re-export — prefer crimelens_ml.evaluation. """

from crimelens_ml.evaluation import evaluate_classification, evaluate_clustering, evaluate_multiclass_auc

__all__ = ["evaluate_classification", "evaluate_clustering", "evaluate_multiclass_auc"]
