# CrimeLens engineered feature catalog

See also: `crimelens_ml.feature_engineering.FEATURE_CATALOG` (source of truth in code).

| Feature | Formula | Why | Models |
|---------|---------|-----|--------|
| CrimeFrequency7Days | count last 7d | Short-term pressure | D1–D3, D6 |
| CrimeFrequency30Days | count last 30d | Baseline volume | D1–D3, D5–D6 |
| WeekendCrimeRatio | weekend/total 30d | Weekend regime | D1, D3 |
| NightCrimeRatio | night/total 30d | Night ops | D1, D3, D6 |
| FestivalImpactScore | festival × lift | Spike anticipation | D1–D3, D6 |
| CommercialRiskScore | market proximity + footfall | Opportunity crime | D1, D2 |
| PatrolCoverageIndex | patrol / demand | Guardianship gap | D1, D3, D6 |
| CCTVCoverageIndex | cctv density norm | Deterrence | D1–D3 |
| EmergencyResponseScore | inverse response time | Capability | D3, D6 |
| WeatherRiskIndex | precip/vis/temp blend | Context | D1, D2, D4 |
| MobilityScore | traffic × flow | Exposure | D2, D6 |
| RoadAccessibilityScore | connectivity / impedance | Access | D2, D6 |
| HistoricalSimilarityScore | similarity to severe past | Explain/Story analogs | D1, D4, D7 |
| RepeatOffenderScore | network activity | Recidivism | D1, D3, D4 |
| HotspotPersistenceScore | days in hotspot / 30 | Chronic vs acute | D1, D2, D5 |
| SocioEconomicRiskIndex | unemployment/poverty/density/literacy | Structural context | D1, D3, D5 |

All rolling features are point-in-time safe relative to `as_of_ts`.
