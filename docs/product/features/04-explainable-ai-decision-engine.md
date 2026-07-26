# Feature 4 — Explainable AI Decision Engine (XAI)

**Codename:** Explainable AI Decision Engine  
**Status:** Implemented (P1 datathon slice)  
**Primary route:** `/explain`  
**API:** `GET /api/v1/explain/predictions/{value_id}`, `POST .../what-if`, `GET /api/v1/explain/audit`  
**AuthZ:** `prediction:read`  
**Foundation:** wraps existing SHAP explanation artifacts + Decision Card UX + audit trail

---

## Product one-liner

Every risk prediction opens as a **transparent decision file**: plain-language summary, ranked contributing factors, confidence, evidence, similar historical cases, what-if scenarios, and a durable **AI Decision Audit Trail** — so officers can ask *why* and get an answer grounded in model + data, not a black box.

---

## Problem

Black-box AI says: **Crime Risk 93%.** Officers ask: **Why?** Without an answer, public-sector users will not trust or adopt the system.

Comparing Area A (92%) vs Area B (48%) is useless unless the platform explains factors, confidence, evidence, and how the score would change if conditions change.

---

## Positioning

| Surface | Job |
|---------|-----|
| `/prediction` (today) | Scores + raw-ish SHAP chart |
| Feature 1 `/simulation` | City-wide what-if levers |
| Feature 2 `/advisor` | Daily briefing recommendations |
| Feature 3 `/story` | How risk *evolved* over time |
| **Feature 4 `/explain`** | **Prove this prediction** — decision card + audit |

Feature 4 is the **trust layer** over statistical prediction. It must speak **officer language**, not “SHAP value increased.”

---

## Target users

| Persona | Use |
|---------|-----|
| SP / DSP / command | Trust check before acting on a risk score |
| Analyst | Drill factors + evidence + similar cases |
| Oversight / demo judges | Audit trail = accountability story |
| Field planner | What-if patrol / CCTV delta on the same card |

---

## Experience — AI Decision Card

Investigation-file aesthetic: evidence cards, confidence badges, expandable sections, factor chart, comparison table — minimal clutter.

### 1. Decision Summary (top)

Plain language, e.g.:

> High crime risk (**91%**) for the next horizon. Driven mainly by recent similar thefts, weekend activity, commercial proximity, and lower nighttime coverage signals.

Show: risk band, score, horizon, model version, **Observed factors vs model estimate** labels where needed.

### 2. Why did the AI predict this? (factor breakdown)

Humanized feature contributions (from SHAP / local explanation), e.g.:

| Factor (officer label) | Contribution share |
|------------------------|--------------------|
| Previous similar crimes | 42% |
| Weekend activity | 18% |
| Commercial zone | 16% |
| Night time | 12% |
| … | … |

Map internal feature keys (`lag_7d_count`, `weekend_flag`, …) → **friendly labels**. Never lead with ML jargon.

### 3. Confidence meter

Explicit uncertainty band: High / Moderate / Low from model metrics + explanation completeness (not fake 100%).

### 4. Evidence Explorer

Expandable checklist tied to real sources:

- Similar incidents in window (counts / links to map or analytics)  
- Hotspot growth nearby  
- Weekend / time-of-day trend  
- Prediction run + model card pointer  
- Optional socio / density if already in platform  

Everything clickable / traceable.

### 5. What-if & alternative scenarios

Inline scenario compare (not a full Twin rebuild):

| Scenario | Est. risk |
|----------|-----------|
| Current conditions | 91% |
| Extra patrol | 74% |
| Add CCTV | 69% |
| Festival weekend | 97% |

**P1 implementation:** call Feature 1 simulation transform (or a thin shared helper) with preset levers for the selected scope; show delta + one-line why. Deep-link “Open full Simulator.”

### 6. Explainability Timeline (lite)

How *reasoning* for this scope shifted across recent brief/audit snapshots (seeded OK): Mon traffic → Tue festival → … — not a second Story map.

### 7. Similar historical cases

Retrieve nearest prior high-risk windows / stations (seeded narrative + real incident deltas when available):

> Resembles conditions seen in [area] during [period], when vehicle theft rose ~N%.

Mark as **historical analogy** (Observed past), not guaranteed repeat.

### 8. Recommendation justification

If an action is shown:

- Recommendation text  
- Why (tied to top factors)  
- Expected risk reduction (scenario delta)  
- Confidence  

No recommendation without a reason block.

### 9. ⭐ AI Decision Audit Trail (secret weapon)

Persist a reviewable record per explained prediction:

| Field | Content |
|-------|---------|
| What | Predicted score / band / scope / horizon |
| Why | Top factors + NL summary |
| Evidence | Source ids / run ids |
| Confidence | Score + band |
| Recommendation | Optional |
| Outcome (later) | What happened (P2; P1 can show “pending / demo outcome”) |

**P1:** store audit rows in API (DB table or JSON store) + UI list “Recent AI decisions.”  
**P2:** link real incident outcomes for accuracy review.

---

## AI / system approach (honest)

```text
prediction_value + explanation_artifact (SHAP)
    → factor normalization + friendly labels
    → confidence from model metrics + artifact presence
    → evidence assembly (incidents, hotspots, trends)
    → similar-case retrieval (heuristic / seeded)
    → what-if via simulation transform
    → NL summary (template-first; optional Gemini polish on JSON only)
    → audit_trail write
```

Aligns with `docs/ai/ARCHITECTURE.md`: statistical plane owns scores/SHAP; narrative must not invent numbers.

---

## Design principles

- Investigation file, not a data-science notebook  
- Officer language over ML terms  
- Confidence always visible  
- Expandable evidence > dump of arrays  
- Scenario compare in one glance  
- Auditability as a first-class trust signal  

---

## Scope cuts

### In for datathon (P1)

- `/explain` page: pick station/hotspot prediction → full Decision Card  
- Factor bars with friendly labels (from existing SHAP)  
- Confidence meter + NL summary  
- Evidence Explorer (grounded links)  
- Alternative scenarios (3–4) via simulation helper + Simulator link  
- Similar cases (seeded + simple heuristic)  
- Explainability timeline lite (seeded / derived)  
- **Audit trail** list + detail for generated cards  
- Entry points: from `/prediction` “Open Decision Card”  
- API: `GET/POST` explain + audit endpoints wrapping prediction explanation  

### Explicitly out (P2+)

- Real-time online SHAP for every new model train in-demo  
- Claiming causal proof of patrol effectiveness  
- Replacing Feature 1 as the only what-if lab  
- Full regulatory audit export pack (PDF/eSign)  

---

## API sketch (planned)

```http
GET  /api/v1/explain/predictions/{value_id}     # Decision Card payload
POST /api/v1/explain/predictions/{value_id}/what-if
GET  /api/v1/explain/audit                      # recent audit trail
GET  /api/v1/explain/audit/{audit_id}
POST /api/v1/explain/audit                       # persist after view/generate (or auto on GET)
```

**Card payload (conceptual):** `summary`, `score`, `confidence`, `factors[]`, `evidence[]`, `scenarios[]`, `similar_cases[]`, `timeline[]`, `recommendation`, `model`, `disclaimer`, `audit_id`.

Reuse existing explanation schema; enrich rather than duplicate.

---

## Success criteria (demo)

1. From Prediction, open a Decision Card in one click.  
2. Officer sees **why** (top factors in plain language) + confidence.  
3. Expand Evidence → real links/metrics.  
4. Toggle what-if scenario → risk delta updates.  
5. Show Audit Trail entry for that prediction.  
6. Presenter line: *“We don’t just predict — we prove it.”*

---

## Implementation notes (when building)

- Elevate `/prediction` SHAP panel into Decision Card; keep Prediction as list/selector.  
- Friendly label map for known demo features.  
- Prefer server-side card assembly so UI cannot drift.  
- What-if: reuse `simulation` scenario transform scoped to station/cell if possible.  
- Audit: new lightweight table **or** JSON file/module store for hackathon speed — prefer Alembic table if migrations stay easy.  
- Update this doc → **Implemented** when `/explain` ships.

---

## Related docs

- `docs/product/features/01-digital-twin-simulator.md`  
- `docs/product/features/02-strategic-intelligence-advisor.md`  
- `docs/ml/model-governance.md`  
- `docs/ai/ARCHITECTURE.md`  
- Existing prediction explanation API  

---

## After approval

Same sequence as Features 1–3: confirm brief → implement P1 Decision Card + Audit Trail.
