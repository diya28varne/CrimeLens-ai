# MVP scope — P0 / P1 / P2

P0/P1/P2 cuts for datathon vs pilot. Feature-level product briefs live under [`features/`](./features/).

## Datathon brief coverage

| Capability | Status |
|------------|--------|
| Interactive dashboards & geospatial maps | **Map UI live** |
| District-level drilldowns | **Live** |
| Network & link analysis | **Live** |
| Repeat offender tracking | **Live** |
| Socio-economic crime correlation | **Implemented** |
| Predictive risk scoring | **Live** |
| Crime incident store (PostGIS) | **Implemented** |
| **Digital Twin Simulator** | **Live** — `/simulation` |
| **Strategic Intelligence Advisor** | **Live** — `/advisor` |
| **Crime Story Playback** | **Live** — `/story` |
| **Explainable AI Decision Engine** | **Live** — `/explain` |
| **Executive Intelligence Report** | **Live** — `/reports` · [Feature 5](./features/05-executive-intelligence-report.md) |

## Priority cuts

| Priority | Include | Exclude |
|----------|---------|---------|
| **P0/P1** | Features 1–5 (Twin, Advisor, Story, XAI, Reports + Present mode) | Live external feeds, server PDF farm, PPTX |
| **P2** | Outcome-linked audit, richer map snapshots in PDF | Multi-city federation, guaranteed accuracy claims |

## Flagship routes

| Feature | Route |
|---------|-------|
| 1 Twin | `/simulation` |
| 2 Advisor | `/advisor` |
| 3 Story | `/story` |
| 4 Explain | `/explain` |
| 5 Reports | `/reports` |
