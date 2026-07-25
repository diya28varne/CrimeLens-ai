"""Domain tests for socio-economic correlation math."""

from crimelens_domain.socioeconomics import (
    CorrelationInterpretation,
    interpret_correlation,
    pearson_correlation,
)


def test_pearson_perfect_positive() -> None:
    xs = [1.0, 2.0, 3.0, 4.0]
    ys = [2.0, 4.0, 6.0, 8.0]
    r = pearson_correlation(xs, ys)
    assert r is not None
    assert abs(r - 1.0) < 1e-9


def test_pearson_perfect_negative() -> None:
    xs = [1.0, 2.0, 3.0, 4.0]
    ys = [8.0, 6.0, 4.0, 2.0]
    r = pearson_correlation(xs, ys)
    assert r is not None
    assert abs(r + 1.0) < 1e-9


def test_interpret_strong() -> None:
    assert interpret_correlation(0.8, 8) == CorrelationInterpretation.strong_positive
    assert interpret_correlation(-0.75, 8) == CorrelationInterpretation.strong_negative


def test_insufficient() -> None:
    assert pearson_correlation([1.0], [2.0]) is None
    assert interpret_correlation(None, 10) == CorrelationInterpretation.insufficient_data
