"""Enterprise feature engineering for CrimeLens risk / hotspot / advisor."""

from __future__ import annotations

import numpy as np
import pandas as pd

FEATURE_CATALOG: dict[str, dict[str, str]] = {
    "CrimeFrequency7Days": {
        "formula": "count(incidents in cell, last 7 days)",
        "why": "Short-term crime pressure",
        "models": "D1,D2,D3,D6",
    },
    "CrimeFrequency30Days": {
        "formula": "count(incidents in cell, last 30 days)",
        "why": "Baseline volume",
        "models": "D1,D2,D3,D5,D6",
    },
    "WeekendCrimeRatio": {
        "formula": "weekend_incidents_30d / max(total_30d, 1)",
        "why": "Weekend operational regime",
        "models": "D1,D3",
    },
    "NightCrimeRatio": {
        "formula": "night_incidents_30d / max(total_30d, 1)",
        "why": "Night-time risk regime",
        "models": "D1,D3,D6",
    },
    "FestivalImpactScore": {
        "formula": "festival_window_flag * historical_lift (0-1)",
        "why": "Festival-driven spikes",
        "models": "D1,D2,D3,D6",
    },
    "CommercialRiskScore": {
        "formula": "0.5*(1 - dist_market_norm) + 0.5*footfall_index",
        "why": "Opportunity crime near commercial hubs",
        "models": "D1,D2",
    },
    "PatrolCoverageIndex": {
        "formula": "patrol_hours / (area_proxy * demand_proxy)",
        "why": "Guardianship supply vs demand",
        "models": "D1,D3,D6",
    },
    "CCTVCoverageIndex": {
        "formula": "cctv_density normalized 0-1",
        "why": "Detection/deterrence coverage",
        "models": "D1,D2,D3",
    },
    "EmergencyResponseScore": {
        "formula": "1 - clip(response_minutes/60, 0, 1)",
        "why": "Response capability",
        "models": "D3,D6",
    },
    "WeatherRiskIndex": {
        "formula": "0.4*precip_norm + 0.3*(1-visibility_norm) + 0.3*temp_anomaly",
        "why": "Weather-modulated street activity",
        "models": "D1,D2,D4",
    },
    "MobilityScore": {
        "formula": "traffic_index * population_flow_index",
        "why": "Ambient exposure",
        "models": "D2,D6",
    },
    "RoadAccessibilityScore": {
        "formula": "road_connectivity / (1 + travel_impedance)",
        "why": "Escape routes and patrol access",
        "models": "D2,D6",
    },
    "HistoricalSimilarityScore": {
        "formula": "1 - min_distance to past High/Critical feature vectors (proxy)",
        "why": "Analogical risk for Explain/Story",
        "models": "D1,D4,D7",
    },
    "RepeatOffenderScore": {
        "formula": "network activity intensity in catchment 0-1",
        "why": "Recidivism pressure",
        "models": "D1,D3,D4",
    },
    "HotspotPersistenceScore": {
        "formula": "days_in_hotspot_core / 30 clipped",
        "why": "Chronic vs acute hotspot",
        "models": "D1,D2,D5",
    },
    "SocioEconomicRiskIndex": {
        "formula": "z(unemployment)+z(poverty)+z(density)-z(literacy) scaled 0-1",
        "why": "Structural context aligned with Analytics",
        "models": "D1,D3,D5",
    },
}


def _clip01(s: pd.Series) -> pd.Series:
    return s.clip(0.0, 1.0)


def engineer_risk_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build engineered columns from processed cell-level frames."""
    out = df.copy()
    total30 = out.get("incidents_30d", out.get("CrimeFrequency30Days", pd.Series(1, index=out.index))).replace(0, 1)

    if "CrimeFrequency7Days" not in out:
        out["CrimeFrequency7Days"] = out.get("incidents_7d", 0)
    if "CrimeFrequency30Days" not in out:
        out["CrimeFrequency30Days"] = out.get("incidents_30d", 0)

    out["WeekendCrimeRatio"] = _clip01(out.get("weekend_cnt_30d", 0) / total30)
    out["NightCrimeRatio"] = _clip01(out.get("night_cnt_30d", 0) / total30)
    out["FestivalImpactScore"] = _clip01(
        out.get("festival_flag", 0).astype(float) * out.get("festival_lift", 0.35)
    )

    dist_m = out.get("dist_market_m", pd.Series(2000, index=out.index)).astype(float)
    footfall = out.get("footfall_index", pd.Series(0.4, index=out.index)).astype(float)
    out["CommercialRiskScore"] = _clip01(0.5 * (1 - (dist_m / 5000).clip(0, 1)) + 0.5 * footfall)

    patrol = out.get("patrol_hours_7d", pd.Series(10, index=out.index)).astype(float)
    demand = (out["CrimeFrequency7Days"].astype(float) + 1.0)
    out["PatrolCoverageIndex"] = _clip01(patrol / (demand * 2.0))

    out["CCTVCoverageIndex"] = _clip01(out.get("cctv_density", 0).astype(float) / 20.0)
    resp = out.get("avg_response_minutes", pd.Series(25, index=out.index)).astype(float)
    out["EmergencyResponseScore"] = _clip01(1.0 - (resp / 60.0))

    precip = out.get("precip_mm", 0).astype(float)
    vis = out.get("visibility_km", 8).astype(float)
    temp = out.get("temp_c", 28).astype(float)
    out["WeatherRiskIndex"] = _clip01(
        0.4 * (precip / 40).clip(0, 1)
        + 0.3 * (1 - (vis / 10).clip(0, 1))
        + 0.3 * ((temp - 22).abs() / 15).clip(0, 1)
    )

    traffic = out.get("traffic_index", 0.4).astype(float)
    flow = out.get("population_flow_index", 0.4).astype(float)
    out["MobilityScore"] = _clip01(traffic * flow)

    conn = out.get("road_connectivity_score", 0.5).astype(float)
    imped = out.get("travel_impedance", 0.3).astype(float)
    out["RoadAccessibilityScore"] = _clip01(conn / (1.0 + imped))

    # Proxy similarity: invert normalized recent severity distance to "critical profile"
    sev = out.get("severity_high_crit_share_7d", 0.2).astype(float)
    out["HistoricalSimilarityScore"] = _clip01(0.4 + 0.6 * sev)

    out["RepeatOffenderScore"] = _clip01(out.get("repeat_offender_activity_score", 0.2).astype(float))
    out["HotspotPersistenceScore"] = _clip01(out.get("hotspot_days", 0).astype(float) / 30.0)

    u = out.get("unemployment_rate", 6).astype(float)
    p = out.get("poverty_index", 0.25).astype(float)
    d = out.get("population_density", 400).astype(float)
    lit = out.get("literacy_rate", 75).astype(float)
    raw = (u / 15) + p + (d / 5000) - (lit / 100)
    out["SocioEconomicRiskIndex"] = _clip01((raw - raw.min()) / (raw.max() - raw.min() + 1e-6) if len(out) else raw)

    out["feature_set_id"] = out.get("feature_set_id", "risk_v1")
    return out


def derive_risk_labels(df: pd.DataFrame) -> pd.DataFrame:
    """Ordinal risk from engineered intensity — used for synthetic/supervised labels."""
    out = df.copy()
    score = (
        0.22 * out["CrimeFrequency7Days"].rank(pct=True)
        + 0.18 * out["CrimeFrequency30Days"].rank(pct=True)
        + 0.12 * out["NightCrimeRatio"]
        + 0.12 * out["FestivalImpactScore"]
        + 0.10 * out["SocioEconomicRiskIndex"]
        + 0.10 * (1 - out["PatrolCoverageIndex"])
        + 0.08 * out["RepeatOffenderScore"]
        + 0.08 * out["HotspotPersistenceScore"]
    )
    out["risk_score"] = score.clip(0, 1)
    bins = [-0.01, 0.35, 0.55, 0.75, 1.01]
    out["risk_level"] = pd.cut(out["risk_score"], bins=bins, labels=["Low", "Medium", "High", "Critical"]).astype(str)
    return out
