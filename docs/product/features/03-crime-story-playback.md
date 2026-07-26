# Feature 3 — Crime Story Playback & Temporal Intelligence Engine

**Codename:** Crime Story Playback  
**Status:** Implemented (P1 datathon slice)  
**Priority:** P1 for datathon demo · P2 for richer journey / seasonal compare / live event feeds  
**Primary route:** `/story`  
**API:** `GET /api/v1/story/frames|chapters|events|range`, `POST /api/v1/story/detective`, `GET /api/v1/story/journey/{id}`  
**AuthZ:** `incident:read`

---

## Product one-liner

An interactive **temporal investigation surface** that lets officers rewind city crime like a documentary: watch how incidents accumulate into clusters and hotspots, hear grounded AI commentary at key transitions, and pause to **Investigate This Moment** (AI Detective Mode) — not a silent time-lapse.

---

## Problem

Dashboards show the **current** state (hotspot now, count now, chart now). Investigators need the **story**:

- When did this hotspot first appear?  
- Gradual growth or sudden spike?  
- Does it repeat seasonally / yearly?  
- Which areas were affected next?  
- Did a prior intervention coincide with decline?  
- Is there a chain reaction across locations?  

Today that means manually stitching reports. Story Playback makes the narrative **visible and queryable**.

---

## Positioning

| Surface | Job |
|---------|-----|
| `/map` | Live / filtered current incidents |
| `/analytics` | Aggregates and charts |
| Feature 1 `/simulation` | *What if we change X going forward?* |
| Feature 2 `/advisor` | *What should we care about today?* |
| **Feature 3 `/story`** | *How did this situation develop over time?* |

**Not** “heatmap with a scrubber.” The product promise is **crime story investigation**.

---

## Target users

| Persona | Use |
|---------|-----|
| Analyst / investigation cell | Reconstruct hotspot birth → growth → decline |
| SP / DSP briefing | Play a 60–90s story clip in a review meeting |
| Control room | Filter by offense; jump to festival / rain markers |
| Demo judge | Play → pause → **Investigate This Moment** |

---

## Experience — Crime Story Playback

Cinematic but command-center: dark theme, soft motion, clear legend, focus on change over time.

### 1. Playback stage (center)

Full-bleed (within app shell) Bengaluru map. Incidents appear/accumulate by cursor time. Optional density / cluster layer that strengthens as points pile up in a cell (hotspot “birth” visual).

### 2. Timeline controller (bottom — video-player metaphor)

- Play / Pause  
- Step back / forward (day or bucket)  
- Speed: 0.5× / 1× / 2× / 4×  
- Scrubber + jump-to-date  
- Range picker (e.g. last 30 / 90 days — full year if seed allows)  
- Filters: offense family, district (and station if cheap)  

### 3. AI narrated insights (side or lower-third)

Not continuous chatter. **Chapter cards** fire at detected transitions, e.g.:

- Cluster emergence  
- Spike vs prior window  
- New neighboring hotspot  
- Decline after a marked “intervention” or event  

Each card: short intelligence sentence + **Observed** badge + link to evidence (counts, bbox, dates). No invented causality; coincidence language when uncertain (“coincides with…”, “followed by…”).

### 4. Crime Journey (P1 lite / P2 full)

Select one incident → lifecycle strip:

Reported → (status transitions if present) → nearby similar → pattern / hotspot association → closed (if status allows).

**P1:** simplified journey from incident fields + nearby count in time window.  
**P2:** richer evidence / network links.

### 5. Hotspot birth & growth

Dedicated viz mode: cells progress Individual → Small cluster → Growing → Emerging hotspot → Critical → Easing (driven by rolling spatial density thresholds — deterministic).

### 6. Seasonal / period compare (P1 lite)

Split or overlay two ranges (e.g. Weekday vs Weekend, or Window A vs B) with delta callouts — not full multi-year climate unless data supports it.

### 7. Pattern Replay (filters)

Replay **only** selected offense families (theft, burglary, violent, etc.) so each category tells its own story.

### 8. Interactive event markers (timeline rail)

Seeded markers: Festival, Holiday, Heavy Rain, Metro disruption, Election (demo set). Align with Simulation Scenario Library themes where useful.

### 9. ⭐ AI Detective Mode — “Investigate This Moment”

**Secret weapon.** At any scrub position:

1. User clicks **Investigate This Moment** → playback pauses.  
2. Panel opens with grounded answers for the **selected window** (e.g. ±3–7 days around cursor, or visible range):  
   - Why did volume rise here? (offense mix, hour-of-day, spatial focus — from data)  
   - What changed vs the prior equal-length window?  
   - Were similar spikes seen in an earlier seeded period?  
   - Which nearby areas rose next (spillover)?  
   - Repeat-offender / link hints if network data intersects the window  
   - Optional: “Try related response in Simulator” deep-link  
3. Reuses Advisor-style orchestration + optional Copilot ask — **must work without Gemini** via templates.

This turns playback into an **interactive temporal investigation engine**.

---

## AI / system approach (honest)

```text
Incidents (time + geom)
    → bucketed frames (day / 6h)
    → spatial density / simple clustering per frame
    → transition detection (spike, new cluster, decline)
    → narrative chapter templates (+ optional LLM polish on tool JSON)
    → Detective Mode brief for paused window
```

- **No silent random animation** — every frame is queryable state.  
- **No invented patrol outcomes** unless seeded as event markers / demo annotations.  
- Align with `docs/ai/ARCHITECTURE.md`: tools cite; humans decide.

---

## Design principles

- Cinematic **and** professional — soft accumulation, not fireworks  
- Dark ops theme; minimal chrome during play  
- Clear legends (offense color, hotspot intensity, event markers)  
- Motion serves comprehension (growth/decline), not decoration  
- Narration sparse and high-signal  
- Detective Mode feels like an analyst pull-up, not a chat takeover  

---

## Scope cuts

### In for datathon (P1)

- `/story` page: map + timeline controller (play/pause/speed/scrub/range)  
- Incident points accumulate by time; offense + district filters  
- Hotspot intensity layer from rolling density (birth/growth/decline)  
- 4–8 AI narrative chapters at detected transitions (template-grounded)  
- Event markers (seeded) on the timeline  
- Period compare lite (two presets or A/B range)  
- **AI Detective Mode** for paused cursor window  
- API for frames / chapters / detective brief  
- Nav: **Story**  

### Explicitly out (P2+)

- True Netflix-grade documentary rendering  
- Full multi-year climate without data  
- Automatic causal claims about patrol effectiveness  
- Frame-perfect sync to external live cameras / weather APIs  
- Replacing `/map` as the only spatial tool  

---

## API sketch (planned)

```http
GET  /api/v1/story/range?from=&to=&offense=&district_id=
GET  /api/v1/story/frames?from=&to=&bucket=day&offense=&district_id=
GET  /api/v1/story/chapters?from=&to=&offense=&district_id=
GET  /api/v1/story/events?from=&to=
POST /api/v1/story/detective          # { cursor_at, window_days, filters }
GET  /api/v1/story/journey/{incident_id}   # P1 lite OK
```

**Frame (conceptual):** `t`, `incident_ids[]` or GeoJSON delta, `density_cells[]`, `counts`.  
**Chapter:** `t_start`, `t_end`, `title`, `narrative`, `kind: observed`, `metrics`, `sources`.  
**Detective:** Advisor-like brief scoped to window + map bbox hint.

---

## Success criteria (demo)

1. Scrub/play 30–90 days; points and density visibly evolve.  
2. At least one chapter appears at a real spike / new cluster.  
3. Filter to one offense family → clear alternate story.  
4. Click event marker → context chip.  
5. **Investigate This Moment** → grounded panel with Observed metrics + optional Simulator link.  
6. Presenter line: *“We don’t just show where — we rewind how it became a hotspot.”*

---

## Implementation notes (when building)

- Reuse MapLibre + deck.gl from `/map`; prefer **precomputed frames** for smooth play (client buffer).  
- Seed enough dated incidents across months if current seed is too short.  
- Chapter detection = deterministic rules on frame metrics (threshold deltas).  
- Detective Mode can call shared helpers with Advisor service patterns.  
- Keep payload sizes bounded (bbox + offense filters; simplify geometry).  
- Update this doc → **Implemented** and `mvp-scope.md` when `/story` ships.

---

## Related docs

- `docs/product/mvp-scope.md`  
- `docs/product/features/01-digital-twin-simulator.md`  
- `docs/product/features/02-strategic-intelligence-advisor.md`  
- `docs/architecture/PHASE_MAP.md`  
- `docs/ai/ARCHITECTURE.md`  

---

## After approval

Same sequence as Features 1–2: confirm brief → implement P1 slice (playback + chapters + Detective Mode).
