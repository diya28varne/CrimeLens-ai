"""Pearson correlation utilities (stdlib-only, no SciPy required)."""

from __future__ import annotations

import math
from enum import Enum
from typing import Sequence


class CorrelationInterpretation(str, Enum):
    strong_positive = "strong_positive"
    moderate_positive = "moderate_positive"
    weak_positive = "weak_positive"
    negligible = "negligible"
    weak_negative = "weak_negative"
    moderate_negative = "moderate_negative"
    strong_negative = "strong_negative"
    insufficient_data = "insufficient_data"


def pearson_correlation(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    """Return Pearson r, or None if undefined (n<2 or zero variance)."""
    n = min(len(xs), len(ys))
    if n < 2:
        return None
    x = list(xs)[:n]
    y = list(ys)[:n]
    mean_x = sum(x) / n
    mean_y = sum(y) / n
    num = sum((a - mean_x) * (b - mean_y) for a, b in zip(x, y, strict=True))
    den_x = math.sqrt(sum((a - mean_x) ** 2 for a in x))
    den_y = math.sqrt(sum((b - mean_y) ** 2 for b in y))
    if den_x == 0.0 or den_y == 0.0:
        return None
    return num / (den_x * den_y)


def interpret_correlation(coefficient: float | None, sample_size: int) -> CorrelationInterpretation:
    if coefficient is None or sample_size < 3:
        return CorrelationInterpretation.insufficient_data
    r = coefficient
    ar = abs(r)
    if ar < 0.2:
        return CorrelationInterpretation.negligible
    if ar < 0.4:
        return (
            CorrelationInterpretation.weak_positive
            if r > 0
            else CorrelationInterpretation.weak_negative
        )
    if ar < 0.7:
        return (
            CorrelationInterpretation.moderate_positive
            if r > 0
            else CorrelationInterpretation.moderate_negative
        )
    return (
        CorrelationInterpretation.strong_positive
        if r > 0
        else CorrelationInterpretation.strong_negative
    )
