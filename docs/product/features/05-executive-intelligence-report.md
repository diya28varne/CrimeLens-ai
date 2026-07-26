# Feature 5 — One-Click Executive Intelligence Report Generator

**Codename:** Executive Intelligence Report  
**Status:** Implemented (P1 datathon slice)  
**Primary route:** `/reports`  
**API:** `GET /api/v1/reports/templates`, `POST /api/v1/reports/generate`, `GET /api/v1/reports/{id}`  
**AuthZ:** `analytics:read`

---

## Product one-liner

A one-click **AI intelligence briefing system** that assembles grounded platform analytics into a commissioner-ready report (executive summary, trends, hotspots, predictions, XAI, recommendations, maps/charts, action checklist) — plus **Present Report** interactive briefing mode. Not a dumb “Download PDF” of the current screen.

---

## Problem

Officers burn hours exporting charts, screenshotting maps, writing summaries, and building decks for senior meetings. The data already lives in CrimeLens; the gap is **communication and action packaging**.

---

## Positioning

| Surface | Job |
|---------|-----|
| Dashboards / map / prediction | Explore live data |
| Features 1–4 | Simulate, brief daily, rewind stories, prove predictions |
| **Feature 5 `/reports`** | **Package everything into a shareable / presentable briefing** |

The generator **assembles** existing outputs; it must not invent statistics.

---

## Target users

| Persona | Use |
|---------|-----|
| Commissioner / SP staff | One-click weekly / festival brief for meetings |
| Control room | Daily intelligence brief |
| Analyst | District performance pack with evidence links |
| Demo judges | Present Report → guided walkthrough |

---

## Experience

### 1. Report builder (inputs)

Officer selects:

- Date range (or preset: last 7 / 30 days)  
- District (default BLR / all allowed)  
- Crime categories (optional multi-select)  
- **Report type**  

**P1 templates:**

| Type | Purpose |
|------|---------|
| Daily Intelligence Brief | Compact overnight → morning pack |
| Weekly Crime Analysis | Default demo template |
| Festival Security Assessment | Event-oriented (ties to Twin presets) |

**P2+:** Monthly executive, district performance, emergency incident summary.

Then: **Generate Report** → loading → briefing ready in seconds.

### 2. Cover page

Official tone:

- CrimeLens AI  
- AI-Powered Crime Intelligence Report  
- Prepared for: Karnataka State Police  
- Date / range  
- Classification: Internal Intelligence Brief  
- Report type + generated timestamp + model/data freshness note  

### 3. Sections (assembled from live modules)

| Section | Source (grounded) |
|---------|-------------------|
| Executive Summary | Advisor-style summary + dashboard delta |
| Crime Overview | KPIs, severity/offense mix, WoW/MoM |
| AI Insights | Patterns from Advisor / analytics narrative |
| Hotspot Analysis | Current hotspots + risk bands |
| Prediction | Current risk scores; **Forecast** labeled |
| Explainable AI Summary | Top factors from Feature 4 (aggregate or top station) |
| Operational Recommendations | Advisor actions + Twin preset hints |
| Resource Planning | Lite deployment suggestions derived from risk deltas |
| Maps & Visualizations | Embedded chart images / map snapshots (or print-CSS of live widgets) |
| Action Checklist | Checkbox list of immediate actions |

Always separate **Observed** vs **Forecast** in language and badges.

### 4. Export

- **Print / Save as PDF** via browser print stylesheet (hackathon-reliable)  
- Optional server PDF later (P2)  

### 5. ⭐ AI Interactive Briefing Mode (secret weapon)

**Present Report** enters full-screen / focus presentation:

- Section-by-section AI narration (template-grounded script from the same payload)  
- Next / Previous / Jump to section  
- Click chart or hotspot → drill to `/map`, `/prediction`, `/explain`, `/story` with context  
- Feels like a command-center brief, not a static file  

P1: in-app presenter with spoken-style text panels (no TTS required).  
P2: optional TTS / slide export.

---

## AI / system approach (honest)

```text
dashboard + analytics + predictions + hotspots
    + advisor brief helpers
    + explain factors (top scope)
    → report JSON payload (single orchestrator)
    → NL section templates (Gemini optional polish on JSON only)
    → Web briefing view + print CSS
    → Present mode (same payload, section script)
```

No free-form hallucination of counts. Every number cites a source field in the payload.

---

## Design principles

- Official government document feel: clean type, clear headings, restrained color  
- Concise language for executives  
- Labeled visuals; no decorative clutter  
- Credibility > flash  
- Action checklist ends the brief  

---

## Scope cuts

### In for datathon (P1)

- Replace `/reports` placeholder with generator UI  
- Templates: **Daily** + **Weekly** (+ Festival as third if cheap)  
- Orchestrator API returns full report JSON  
- On-screen briefing with cover → sections → checklist  
- Print-to-PDF stylesheet  
- **Present Report** interactive mode with section narration + drill-out links  
- Nav already has Reports — wire it  

### Explicitly out (P2+)

- Pixel-perfect Word/PPTX corporate templates  
- Server-side Chromium PDF farm (unless easy)  
- Auto-email distribution lists  
- Invented resource budgets without model basis  

---

## API sketch (planned)

```http
GET  /api/v1/reports/templates
POST /api/v1/reports/generate
     # { template, from, to, district_id?, offense_codes? }
GET  /api/v1/reports/{report_id}          # optional cache
```

**Payload (conceptual):** `meta`, `cover`, `executive_summary`, `overview`, `insights[]`, `hotspots[]`, `predictions[]`, `xai_summary`, `recommendations[]`, `resource_plan[]`, `checklist[]`, `charts` (series data), `sources[]`, `presenter_script[]`, `disclaimer`.

---

## Success criteria (demo)

1. Click Generate → complete Weekly brief in &lt;5s.  
2. Executive summary readable in &lt;60s.  
3. Hotspots + predictions + XAI factors visible and labeled Observed/Forecast.  
4. Print produces a credible multi-page PDF.  
5. Present Report walks 3+ sections with drill links.  
6. Line: *“From data to decisions in one click.”*

---

## Implementation notes (when building)

- Reuse Advisor / Explain / Dashboard / Prediction services inside one `reports` module.  
- Prefer chart data in JSON + ECharts in UI; for print, render charts before `window.print()`.  
- Map: static snapshot optional; link “Open live map” acceptable for P1 if snapshot is hard.  
- Cache last generated report in memory for Present mode.  
- Update this doc → **Implemented** when `/reports` ships.

---

## Related docs

- Features 1–4 briefs  
- `docs/ai/ARCHITECTURE.md`  
- Existing `(app)/reports/page.tsx` placeholder  

---

## After approval

Same sequence: confirm brief → implement P1 generator + Present mode.
