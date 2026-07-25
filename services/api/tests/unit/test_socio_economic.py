"""Unit tests for socio-economic service math wiring (no DB)."""

from crimelens_domain.socioeconomics import pearson_correlation


def test_demo_unemployment_crime_direction() -> None:
    """Seed values are designed so unemployment rises with crime rate."""
    unemployment = [6.8, 5.4, 5.9, 7.5, 8.1, 9.2, 8.6, 6.2]
    crime_rate = [318.0, 210.0, 245.0, 290.0, 335.0, 380.0, 350.0, 230.0]
    r = pearson_correlation(unemployment, crime_rate)
    assert r is not None
    assert r > 0.7
