# Feature 2 — AI Strategic Intelligence Advisor

**Codename:** Strategic Intelligence Advisor  
**Status:** Implemented (P1 datathon slice)  
**Priority:** P1 for datathon demo · P2 for production pilot (timeline / closed-loop)  
**Primary route:** `/advisor`  
**API:** `GET /api/v1/advisor/brief/current`, `POST /api/v1/advisor/brief/refresh`, `GET /api/v1/advisor/brief/history`  
**Related (do not merge):** `/ai` grounded chat copilot — ask-anything; Advisor is **briefing-first**, not a blank chat box  
**Depends on:** Analytics trends, prediction/hotspots, network/repeat offenders, dashboard overview; optional link to Feature 1 `/simulation`  
**AuthZ:** `analytics:read`

---

## Product one-liner

A 24/7 **crime analyst & decision advisor** that turns authorized platform data into a morning-style intelligence briefing: **what’s happening, why it matters, what may come next, and what actions to consider** — with evidence and confidence, never invented facts.

---

## Problem

Dashboards stop at visualization:

- Crime ↑ 15%  
- Theft highest in Area X  
- Burglary rising  

Officers still must answer: *Why? Is it unusual? Seasonal? Linked to another area? Where do we go first?*

The Advisor closes that gap: **data → insight → recommended action**, while humans keep final judgment.

---

## Positioning

| Surface | Job |
|---------|-----|
| Dashboards / map / prediction | Show the numbers and layers |
| Feature 1 Digital Twin | Answer *what if we change X?* |
| `/ai` Copilot | Answer free-form questions with tools |
| **Feature 2 Advisor** | **Proactive briefing**: interpret, explain, recommend, cite |

**Not a chatbot.** Primary UX is an intelligence command briefing. Optional “Ask about this finding” can deep-link to Copilot later; it must not be the home experience.

---

## Target users

| Persona | Use |
|---------|-----|
| SP / DSP / command staff | Morning brief before ops meeting |
| Control room | Emerging patterns + risk bands by sector |
| Analyst | Evidence drill-down; compare to prior days |
| Demo judge | “Open Advisor → read summary → expand one action” |

---

## Experience — Strategic Intelligence Advisor

Ops briefing room layout (clean hierarchy, expandable evidence — not message bubbles).

### 1. Daily Intelligence Summary (top)

Auto-generated concise overview on load (and on Refresh).

Example shape:

> Crime activity ↑ vs last week; vehicle thefts concentrated near commercial / metro evening hours; two new eastern hotspot clusters; recommend patrol emphasis 19:00–22:00.

Must label **Observed** vs **Forecast** statements in the UI (badges or prefixes).

### 2. Emerging Pattern Detection

Surface **3–5** patterns in natural language, each with:

- Pattern title  
- Short explanation  
- Strength / confidence  
- Evidence handle (expand)

Examples (illustrative): Friday burglary skew; concert-day mobile theft; post-20:00 vehicle theft near malls; weather-linked uplift; repeat-offender adjacency across districts.

### 3. Risk Assessment strip

District / station cards from current prediction run:

- Risk band (High / Medium / Low)  
- Confidence  
- One-line **why it changed** (from SHAP / trend delta / hotspot rank — tool-grounded)

### 4. Action Recommendations

3–5 operational suggestions, each with:

- Action text  
- Why (1–2 sentences)  
- Confidence  
- Evidence panel (expand)  
- Optional: “Test in Simulator” → `/simulation` with a preset/hint (P1 nice-to-have)

Tone: **supports** officers; never issues orders or arrest/disposition language.

### 5. Supporting Evidence (expandable)

On expand of pattern or action, show grounded artifacts:

- Trend sparkline / % vs prior window (analytics)  
- Hotspot / map snapshot link  
- Top contributing factors (SHAP or rule features)  
- Similar past window note (if seedable)  
- Model / brief confidence  
- Citations: API source ids / run ids (same spirit as copilot citations)

### 6. Intelligence Timeline (enhancement — include in design; P1 lite)

Chronological strip of prior brief snapshots:

- What the Advisor said yesterday  
- Recommendations listed  
- Optional demo fields: *acted on?* / *hotspot realized?* / *forecast accuracy note*  

**P1:** seeded / generated history of last N brief runs (even if actions are not truly closed-loop).  
**P2:** real acknowledgment + outcome logging for accountability.

---

## AI / system approach (honest)

**Pipeline (not free-form chat):**

1. **Retrieve** authorized facts via existing modules (trends, current predictions, hotspots, network/repeat, dashboard alerts).  
2. **Score / detect** patterns with deterministic rules + existing model outputs (day-of-week skew, evening concentration, hotspot emergence, risk deltas).  
3. **Narrate** into professional brief language — template-first for datathon reliability; optional Gemini polish **only** over tool payloads (same rule as AI architecture: no invented numbers).  
4. **Persist** brief run for Timeline (JSON snapshot).

Aligns with `docs/ai/ARCHITECTURE.md`: agents/tools cite; prediction plane stays statistical; humans approve ops.

**Gemini:** optional for P1 if keys present; **must degrade** to deterministic grounded templates so demos never blank out.

---

## Design principles

- Intelligence briefing room, not messaging app  
- Clear section hierarchy; readable summaries; professional type  
- Confidence indicators everywhere recommendations appear  
- Expandable evidence > wall of charts on first paint  
- Minimal clutter; calm dark ops theme consistent with shell  
- Always disclose estimate vs observation  

---

## Scope cuts

### In for datathon (P1)

- `/advisor` page: Summary, Patterns (3–5), Risk cards, Actions (3–5), Evidence expand  
- Intelligence Timeline (lite): last N brief snapshots  
- API: `GET /api/v1/advisor/brief/current` (+ optional `GET .../brief/history`)  
- Grounding from live analytics / prediction / network endpoints (server-side orchestration)  
- Observed vs forecast labels; confidence; citations / source run ids  
- Nav item **Advisor**; keep `/ai` as separate Copilot  

### Explicitly out (P2+)

- Autonomous dispatch / closed-loop command  
- Inventing incidents or unverifiable causal claims  
- Replacing Feature 1 simulation engine  
- Full learning system with real outcome feedback loops (beyond seeded timeline)  
- Requiring Gemini for the page to function  

---

## API sketch (planned)

```http
GET  /api/v1/advisor/brief/current     # generate or return cached daily brief
GET  /api/v1/advisor/brief/history     # timeline (limit)
POST /api/v1/advisor/brief/refresh     # optional force rebuild
GET  /api/v1/advisor/brief/{id}        # one snapshot + evidence payloads
```

**Brief payload (conceptual):** `summary`, `patterns[]`, `risk_areas[]`, `actions[]`, `evidence{}`, `timeline_meta`, `generated_at`, `disclaimer`, `sources[]`.

Envelope follows existing `{ data: ... }` API style.

---

## Success criteria (demo)

1. Open `/advisor` → readable **Today’s Intelligence Summary** in &lt;2s (cached) / &lt;5s cold.  
2. Show ≥3 patterns and ≥3 actions with confidence.  
3. Expand one action → evidence (trend + hotspot/risk source) visible.  
4. Timeline shows ≥2 prior days (seeded OK).  
5. Presenter line: *“Not just graphs — insight and what to do next.”*  

---

## Implementation notes (when building)

- Prefer **one orchestrator service** that calls internal services / SQL — don’t duplicate ML.  
- Reuse copilot tool logic where possible; Advisor UI must not be a chat shell.  
- Seed a few historical brief JSON rows for Timeline if live history is empty.  
- Link actions to Simulation presets when the lever mapping is obvious (festival → Weekend Festival).  
- Update this doc → **Implemented** and `mvp-scope.md` when `/advisor` ships.  

---

## Relationship to Challenge 2

Strengthens **analytics, explainability, and operational decision support** without reducing the product to a chatbot — pairs with Feature 1 (simulate decisions) and Copilot (ad-hoc Q&A).

---

## Related docs

- `docs/product/mvp-scope.md`  
- `docs/product/features/01-digital-twin-simulator.md`  
- `docs/ai/ARCHITECTURE.md`  
- Existing `/ai` copilot feature (keep separate product surface)

---

## After approval

When you’re happy with this brief, we convert it into a focused Cursor build prompt (P1 slice only), then implement — same sequence as Feature 1.
