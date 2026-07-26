# Feature 1 — AI Crime Digital Twin Simulator

**Codename:** Decision Simulation Center  
**Status:** Implemented (P1 datathon slice)  
**Priority:** P1 for datathon demo · P2 for production pilot  
**Primary route:** `/simulation`  
**API:** `GET /api/v1/simulation/scenarios`, `POST /api/v1/simulation/runs`  
**Depends on:** Prediction hotspots, spatial map, auth/RBAC (`prediction:read`)

---

## Product one-liner

A virtual replica of city crime dynamics that lets police **test operational “what-if” decisions** and see projected risk shifts before committing real resources.

---

## Problem

Commanders today ask questions that dashboards cannot answer with confidence:

- What if we add 20 patrol units this weekend?
- What if we install CCTV along Metro Corridor A?
- What happens to risk during a festival or heavy rain?
- Which areas become vulnerable if a station closes?

Historical maps and static predictions answer *where crime is*. The Digital Twin answers *what happens if we change something*.

---

## Positioning

| Today (CrimeLens baseline) | With Digital Twin |
|----------------------------|-------------------|
| Where is crime happening? | What will happen if we change X? |
| Reporting & monitoring | Decision support & planning |
| Heatmaps / scores | Scenario → outcome briefing |

This feature turns CrimeLens from a console into an **operations decision lab**.

---

## Target users

| Persona | Use |
|---------|-----|
| SP / DSP / Commissioner staff | Compare deployment options before briefing |
| Control room / ops planner | Load festival / VIP templates; adjust patrols |
| Analyst | Stress-test hotspot forecasts under interventions |
| Demo judge / stakeholder | One-click Scenario Library walkthrough |

---

## Experience — Decision Simulation Center

Four-region layout (command-center, not dashboard clutter):

### 1. Left — Scenario Builder

Intuitive controls (sliders, toggles, dropdowns), not raw model params.

**Hackathon control set (MVP):**

| Control | Type | Effect (illustrative) |
|---------|------|------------------------|
| Patrol units | Slider (−50% … +50%) | Coverage ↑ → local risk ↓ |
| CCTV coverage | Slider / zone picker | Deterrence in selected sectors |
| Public event | Toggle + zone | Risk ↑ near venue + spillover |
| Time of day | Dropdown | Night / evening multipliers |
| Day type | Dropdown | Weekday / weekend / holiday |
| Weather stress | Toggle (optional) | Heavy rain → selected crime types ↑ |

**Out of MVP (pilot later):** road closure, new station, live traffic feeds, real weather APIs, cost optimization solvers.

### 2. Center — Interactive city map

Reuse MapLibre + deck.gl patterns from `/map` and `/prediction`.

**MVP layers:**

- Baseline crime / hotspot intensity  
- Simulated risk overlay (delta or absolute)  
- Police stations (existing org GIS if available)  
- Scenario markers (event zone, CCTV emphasis)

**Pilot layers:** patrol routes, live traffic, population density, camera inventory.

Map should update when scenario inputs change (debounce ~300–500ms). Prefer clear legend + color-blind-safe diverging palette for *increase / decrease*.

### 3. Right — AI prediction summary (ops briefing)

Read like an intelligence brief, not an ML dump:

- **Current scenario** — short label from library or custom  
- **Predicted change** — 2–4 bullet deltas by corridor / sector  
- **Suggested actions** — 2–3 operational next steps  
- **Confidence** — model/estimate confidence with disclaimer  

Always show: *Estimates from a decision model — not guarantees.*

### 4. Bottom — Comparison view

**Current state vs Simulated state** for a small metric set:

| Metric (MVP) | Source idea |
|--------------|-------------|
| Aggregate crime risk | Mean / sum of grid scores |
| Hotspot cell count above threshold | Count of cells |
| Patrol coverage index | Function of patrol slider + station proximity |
| Resource utilization | Normalized patrol / CCTV knobs |
| Est. relative ops cost | Simple weighted cost of levers |

---

## Scenario Library (required for demos)

One-click templates users can load, tweak, and compare:

| Template | Default levers |
|----------|----------------|
| Weekend Festival | Event on, weekend, patrol +15%, CCTV +10% near venue |
| Heavy Rain | Weather stress on, evening window |
| VIP Movement | Event corridor, patrol +25%, CCTV +20% along route |
| Major Sporting Event | Event on, weekend, spillover zones |
| School Holiday | Day type holiday, selected residential risk shift |
| Metro Service Disruption | Corridor stress, alternate-route spillover |

Library entries are **JSON scenario presets** (UI + API), not separate models.

---

## AI / model approach (honest)

Not random; also not claiming causal perfection.

**Inputs (MVP):** historical hotspot / prediction grids, time-of-day, day type, scenario levers, optional coarse socio-economic context already in platform.

**Engine (datathon-realistic):**

1. Start from **current prediction / hotspot run** (existing `prediction_*` APIs).  
2. Apply a documented **scenario transform** (rule + weighted multipliers per lever × zone).  
3. Produce **simulated grid + deltas + briefing text** (template or grounded AI narration over tool outputs).  
4. Persist optional **simulation run** id for compare / audit (pilot).

**Not in MVP:** online retraining, true counterfactual causal ML, live multi-agency feeds.

Agents (copilot) may later *call* simulation tools; they should not invent numbers outside tool results.

---

## Design principles

- Ops-center aesthetic: calm dark UI, minimal chrome, clear legends  
- Smooth but purposeful transitions (map layer morph / brief refresh)  
- Color-blind-friendly risk deltas  
- No decorative motion that obscures analysis  
- Always disclose model-estimate nature of outputs  

Align with existing shell (`(app)` layout); avoid a separate marketing-site look.

---

## Scope cuts

### In for datathon (P1)

- `/simulation` page with 4-region layout  
- Scenario Builder with ≤6 controls  
- Scenario Library (6 presets)  
- Map: baseline vs simulated risk  
- Briefing panel + comparison strip  
- API: `POST /api/v1/simulation/runs` (or `/decision/simulate`) returning grid + metrics + briefing payload  
- RBAC: reuse `prediction:read` initially; add `simulation:run` when writing audit rows  
- Disclaimer banner  

### Explicitly out (P2+)

- Live traffic / weather / camera inventory integrations  
- Full patrol routing optimizer  
- Multi-city federation  
- Guaranteed accuracy claims  
- Feature 2 (Strategic Intelligence Advisor) coupling beyond shared tools  

---

## API sketch (planned)

```http
GET  /api/v1/simulation/scenarios          # library presets
POST /api/v1/simulation/runs               # { preset_id?, controls, jurisdiction }
GET  /api/v1/simulation/runs/{id}          # optional persistence
```

**Response (conceptual):** `baseline_summary`, `simulated_summary`, `deltas[]`, `geojson_or_grid`, `briefing`, `confidence`, `disclaimer`.

Exact shapes follow `docs/api/REST_API.md` envelope when implemented.

---

## Success criteria (demo)

1. Judge loads **Weekend Festival** in one click.  
2. Map and briefing update within ~1s of control change (cached baseline).  
3. Comparison strip shows clear trade-off (e.g. risk ↓ vs cost ↑ when patrols increase).  
4. Presenter can say: *“We test decisions before we deploy.”*  

---

## Implementation notes (when building)

- Reuse MapLibre/deck.gl from map + prediction features.  
- Prefer server-side scenario transform so UI cannot drift from API.  
- Seed 1–2 demo jurisdictions (Bengaluru-oriented) consistent with existing seeds.  
- Add nav item **Simulation** only when route ships.  
- Update this doc status → **Implemented** and `mvp-scope.md` when live.

---

## Related docs

- `docs/product/mvp-scope.md` — priority table  
- `docs/ai/ARCHITECTURE.md` — tools vs ML separation  
- `docs/database/SCHEMA.md` — `prediction_*`, decision/patrol  
- `docs/architecture/PHASE_MAP.md` — map stack to reuse  

---

## Next feature

**Feature 2 — AI Strategic Intelligence Advisor:** an analyst that reasons over evidence, explains patterns, and recommends actions (complements simulation; does not replace it). Design separately before implementation.
