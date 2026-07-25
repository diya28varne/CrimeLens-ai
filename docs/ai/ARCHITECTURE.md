# CrimeLens AI — AI Architecture Design

**Status:** Design only — no implementation  
**Product role:** Grounded, AuthZ-scoped, explainable intelligence for Karnataka State Police  
**Runtime home:** `services/api` (AI module) + `services/worker` (async briefs/embeddings) + `services/ml` (prediction/SHAP)  
**Related docs:** `docs/database/SCHEMA.md`, `docs/api/REST_API.md`, ADR-0002/0004 (superseded where noted below)

---

## 1. Vision

CrimeLens AI does **not** let a model “guess crime.” It runs a **tool-grounded agent system** that:

1. Retrieves authorized facts (incidents, spatial layers, forecasts, networks, SOPs)  
2. Reasons over those facts with Gemini  
3. Cites sources  
4. Separates **statistical prediction** (ML + SHAP) from **linguistic reasoning** (LLM agents)  
5. Audits every tool call under the user’s jurisdiction  

**Non-goal:** Autonomous arrest/dispatch decisions. Humans approve operational actions.

---

## 2. Architecture overview

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                     ENGINEERING PLANE (builders)                         │
│              Google Antigravity (IDE / Manager / CLI / SDK)               │
│         Build, verify, refactor CrimeLens; not the officer runtime       │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                     OFFICER RUNTIME PLANE (production)                   │
│  Next.js Copilot UI ──SSE──► FastAPI /ai/*                               │
│                                │                                         │
│                    ┌───────────▼───────────┐                             │
│                    │   LangGraph Runtime    │                             │
│                    │  (Agent Workflow)      │                             │
│                    └───────────┬───────────┘                             │
│           ┌────────────┬───────┼───────┬──────────────┐                  │
│           ▼            ▼       ▼       ▼              ▼                  │
│      Prompt/Policy  Memory   MCP    Gemini         Guardrails            │
│      Engineering    Store   Tools   (reason)       AuthZ/PII             │
│                        │       │                                         │
│              ┌─────────┴──┐    ├─ analytics_tool                         │
│              │  Qdrant    │    ├─ spatial_tool                           │
│              │  (RAG)     │    ├─ prediction_tool (+ SHAP fetch)         │
│              └────────────┘    ├─ network_tool                           │
│                                ├─ decision_tool (read/recommend only)    │
│                                └─ docs_rag_tool (Qdrant)                 │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                     PREDICTION PLANE (statistical)                       │
│   PostGIS features → ML pipelines → scores + SHAP → prediction_* tables  │
│   Agents READ predictions; they do NOT retrain models in chat            │
└─────────────────────────────────────────────────────────────────────────┘
```

### Plane separation (critical)

| Plane | What it does | What it must not do |
|-------|----------------|---------------------|
| **Prediction Engine** | Forecast/risk/hotspot/repeat scores + SHAP | Chat with officers |
| **LangGraph Agent** | Reason, retrieve, narrate, cite | Invent numbers without tools |
| **Antigravity** | Help engineers build CrimeLens | Serve as the police production chat API |

---

## 3. Component catalog

### 3.1 Gemini

**What it is:** Google’s LLM family used as the **reasoning and narrative** engine.

**Role in CrimeLens:**
- Intent understanding (ask / brief / explain)  
- Multi-step plan verbalization inside LangGraph nodes  
- Final answer synthesis from tool results  
- Optional structured JSON extraction for brief sections  

**Model strategy (design):**

| Workload | Model tier | Why |
|----------|------------|-----|
| Interactive copilot turns | Gemini Flash (latest agent-optimized Flash line) | Latency + cost |
| Command briefs / deep explain | Gemini Pro (latest Pro line) | Higher reasoning quality |
| Embeddings for RAG | Gemini Embedding model | Populate Qdrant |

**Constraints:**
- Temperature low for operational answers (e.g. 0.1–0.3)  
- Strict output contract: answer + citations + confidence language  
- No free-form SQL generation — only MCP tools  

**Interfaces:**
- Called only from LangGraph LLM nodes / tool-selection nodes  
- API keys via env (`GEMINI_API_KEY`); never in prompts or logs  

---

### 3.2 LangGraph

**What it is:** Stateful graph orchestrator for multi-step agents (nodes, edges, checkpoints, conditional routing).

**Why LangGraph (this phase):**  
CrimeLens needs **explicit, auditable control flow**: retrieve → tool loop → ground → respond → persist. LangGraph makes that graph visible, testable, and interruptible.

> **ADR note:** Earlier revision preferred PydanticAI for hackathon speed. This AI architecture **selects LangGraph as the production orchestrator** for multi-step police workflows. PydanticAI may still wrap individual typed tools if useful, but the **workflow spine is LangGraph**.

**Role:**
- Own the **Agent Workflow** (see §5)  
- Hold short-term graph state (messages, tool results, scope, citations)  
- Enforce max tool iterations / timeouts  
- Emit SSE events (`token`, `tool_start`, `tool_end`, `citation`, `done`)  

**State schema (logical):**

| Field | Purpose |
|-------|---------|
| `auth` | AuthContext snapshot (user, roles, jurisdictions) |
| `mode` | `ask` \| `brief` \| `explain` |
| `scope` | district/station/time window |
| `messages` | conversation turns |
| `retrieval` | Qdrant hits |
| `tool_results` | ordered tool outputs |
| `citations` | accumulated citations |
| `safety_flags` | denials, redactions |
| `finish_reason` | completed / refused / degraded |

**Checkpointer:** Postgres or Redis-backed graph checkpoint for resume/debug (design-time choice: Redis for S0).

---

### 3.3 Google Antigravity

**What it is:** Google’s **agentic development platform** (IDE / Agent Manager / CLI / SDK / Gemini API managed-agent surfaces) for planning, executing, and verifying software tasks across editor, terminal, and browser. See [Google Antigravity](https://antigravity.google/blog/introducing-google-antigravity) and [Developers Blog](https://developers.googleblog.com/build-with-google-antigravity-our-new-agentic-development-platform/).

**Role in CrimeLens (precise):**

| Use | Description |
|-----|-------------|
| **Engineering cockpit** | Developers use Antigravity to scaffold modules, write tests, run Compose, verify UI flows |
| **Agent Manager** | Parallel engineering agents (e.g. “implement spatial router tests”, “update OpenAPI”) |
| **CLI/SDK (optional)** | Internal automation for repo tasks; **not** exposed to police users |
| **Governance patterns** | Adopt enterprise ideas (immutable traces, agent identity concepts) when hardening for agency deploy |

**What Antigravity is NOT in CrimeLens:**
- Not the `/api/v1/ai/chat` runtime for officers  
- Not a substitute for PostGIS/AuthZ tools  
- Not allowed to hold production police PII workspaces without agency policy controls  

**Boundary rule:**  
`Antigravity → builds CrimeLens`  
`LangGraph + Gemini + MCP → runs CrimeLens intelligence for users`

---

### 3.4 MCP (Model Context Protocol)

**What it is:** Standard protocol for exposing **tools/resources** to agents in a consistent, interoperable way.

**Role:**
- Define CrimeLens capabilities as **MCP tools** with JSON schemas  
- Keep LangGraph tool nodes thin: call MCP, don’t embed SQL  
- Allow future alternate orchestrators (or Antigravity custom agents in eng plane) to reuse the same tools  

**MCP server (logical):** `crimelens-mcp` (in-process for S0; separate process at S2)

**Tool registry (allowlisted):**

| Tool | Reads | Writes | AuthZ |
|------|-------|--------|-------|
| `get_dashboard_overview` | aggregates | no | jurisdiction |
| `get_analytics_trends` | trends | no | jurisdiction |
| `search_incidents` | incidents | no | jurisdiction |
| `spatial_bbox_incidents` | Geo query | no | jurisdiction |
| `spatial_radius_search` | Geo query | no | jurisdiction |
| `get_current_predictions` | prediction_values | no | jurisdiction |
| `get_prediction_explanation` | SHAP artifact | no | jurisdiction |
| `get_hotspots_current` | hotspot features | no | jurisdiction |
| `get_network_graph` | persons/links | no | jurisdiction + PII policy |
| `get_repeat_offenders` | ranked persons | no | jurisdiction |
| `recommend_patrol_plan` | decision service | no* | jurisdiction (*creates draft plan only) |
| `rag_search_docs` | Qdrant | no | doc jurisdiction tags |
| `get_model_card` | model_registry | no | prediction:read |

**Hard rules:**
- No `run_sql` tool  
- No `update_incident_status` in v1 agent  
- Every tool receives `AuthContext`  
- Denied tools return `status=denied` and are audited  

---

### 3.5 Qdrant

**What it is:** Dedicated vector database for semantic retrieval.

**Role:** Long-term **AI memory / RAG corpus** for:
- SOPs / police procedure summaries (approved text only)  
- Model cards & metric glossaries  
- Prior generated briefs (non-sensitive or redacted)  
- Ubiquitous language / offense taxonomy descriptions  

**Collections (design):**

| Collection | Payload filters | Content |
|------------|-----------------|---------|
| `sop_chunks` | `district_id?`, `doc_type` | Procedure text |
| `model_cards` | `model_code`, `version` | How to read metrics/SHAP |
| `briefs` | `district_id`, `user_role` | Historical briefs |
| `glossary` | `lang` | Domain terms |

**Payload must include:** `document_id`, `chunk_index`, `source_uri`, `jurisdiction_tags`, `visibility_roles`

**Sync path:**
1. Documents landed in Postgres `documents` / `document_chunks`  
2. Worker embeds via Gemini embeddings  
3. Upsert vectors + payload to Qdrant  
4. Postgres remains catalog/source of truth for text; Qdrant is retrieval index  

> **ADR reconciliation:** S0 may still bootstrap with **pgvector** if ops must stay minimal; **target AI architecture standardizes on Qdrant** for RAG isolation and filter performance. Dual-write period allowed via `VectorStore` port.

---

### 3.6 SHAP

**What it is:** Explainability layer for tree/tabular models (global + local feature attributions).

**Role:** Make Prediction Engine outputs **trustworthy** for command review.

**Where it lives:** `services/ml` offline jobs → `explanation_artifacts` table (and optional object storage for large payloads).

**What SHAP is not:** Not an LLM. Agents **fetch** SHAP via `get_prediction_explanation` and narrate carefully.

**Explanation contract consumed by AI:**

| Field | Meaning |
|-------|---------|
| `base_value` | Model baseline |
| `output_value` | Predicted score/count |
| `global_importance[]` | Feature ranking |
| `local_contributions[]` | This row’s drivers |
| `summary_text` | Optional precomputed seed (still re-validated by agent) |

**Prompt rule:** Agent may paraphrase SHAP but must not invent features that aren’t in the artifact.

---

### 3.7 Prediction Engine

**What it is:** Offline/batch statistical intelligence pipeline (not the LLM).

**Owned by:** `services/ml` + scored tables in Postgres.

**Capabilities:**

| Engine module | Output | Consumed by |
|---------------|--------|-------------|
| Forecast | `incident_count` horizons | Analytics UI + AI briefs |
| Risk scoring | `risk_score` 0–1 by station/grid | Map + patrol |
| Hotspot detection | Hotspot geometries + scores | Map + AI |
| Repeat offender scoring | person risk heuristics/model | Network UI + AI |
| Trend/change signals | deltas / alerts | Dashboard alerts |
| Explain job | SHAP artifacts | Explanation API + AI tool |

**Serving contract for agents:**
- Always include `model_version`, `generated_at`, `is_stale`  
- Prefer **current production** runs (`is_current=true`)  
- Shadow models never shown unless role=`analyst` and flag enabled  

**Boundary:** LangGraph never trains; it only reads Prediction Engine outputs through MCP.

---

## 4. Memory architecture

| Memory type | Store | Lifetime | Contents |
|-------------|-------|----------|----------|
| **Working memory** | LangGraph state | Single turn / graph run | Tool results, citations, scope |
| **Conversation memory** | Postgres `conversations` / `messages` | Days–months | Chat history |
| **Trace memory** | Postgres `tool_traces` | Audit retention policy | Tool IO summaries |
| **Episodic operational memory** | Qdrant `briefs` | Policy-based | Prior brief chunks |
| **Semantic knowledge memory** | Qdrant `sop_chunks`, `glossary`, `model_cards` | Until doc revoked | Approved knowledge |
| **Statistical memory** | `prediction_*`, `hotspot_*` | Per model run | Scores + SHAP |

**Memory hygiene:**
- Purge/redact conversations on admin request  
- Never embed raw PII into Qdrant without redaction pipeline  
- Tool traces store minimized payloads (no secrets, truncated PII)

---

## 5. Agent workflow (LangGraph)

### 5.1 Graph (logical nodes)

```text
START
  → guardrails_in          # auth present, jailbreak/PII policy, rate limit
  → classify_intent        # ask | brief | explain | spatial | network | prediction
  → bind_scope             # district/station/time; clamp to AuthContext
  → retrieve_memory        # Qdrant RAG (role/jurisdiction filtered)
  → plan_tools             # Gemini proposes tool plan (constrained)
  → tool_loop              # MCP calls (max N)
        ├─ on denial → record + continue/alternate
        └─ on error  → degrade path
  → ground_claims          # every numeric/spatial claim maps to tool/RAG evidence
  → synthesize             # Gemini final answer (Flash/Pro by mode)
  → emit_citations         # SSE citation events
  → persist                # messages + tool_traces
  → guardrails_out         # final refusal/redaction check
END
```

### 5.2 Mode-specific paths

| Mode | Extra behavior |
|------|----------------|
| `ask` | Minimal tools; direct Q&A |
| `explain` | Force `get_prediction_explanation` when prediction referenced |
| `brief` | Multi-tool gather → structured sections → optional Pro model |

### 5.3 Degradation ladder

1. Gemini up, tools up → full grounded answer  
2. Gemini up, some tools fail → partial answer + explicit gaps  
3. Gemini down → **no hallucinated brief**; return canned “AI unavailable” + suggest dashboard links  
4. Qdrant down → skip RAG; continue with SQL/MCP tools only  

---

## 6. Tool calling design

### 6.1 Lifecycle

```text
Gemini/plan node
  → validate tool name ∈ allowlist[role]
  → inject AuthContext + clamped scope
  → MCP execute
  → schema-validate response
  → summarize for context window (token budgeter)
  → append citation candidates
  → audit tool_traces
```

### 6.2 Context packing (token budget)

Priority order into Gemini context:
1. System constitution + mode contract  
2. User question  
3. Scope  
4. Tool results (compressed tables)  
5. Top-k Qdrant chunks  
6. Prior conversation (last k turns)

### 6.3 Citation generation

Each tool result yields zero-or-more citations:

```text
{ type, id, label, href? }
```

Synthesize node may only assert facts that appear in tool/RAG packs.

---

## 7. Reasoning design

CrimeLens uses **hybrid reasoning**:

| Layer | Mechanism | Example |
|-------|-----------|---------|
| **Statistical reasoning** | Prediction Engine + SHAP | “Station X risk 0.81; top driver lag_7d_count” |
| **Spatial reasoning** | PostGIS tools | “37 incidents within 500m of point P this week” |
| **Graph reasoning** | Network tools | “Person A co-accused with B in 3 cases” |
| **Linguistic reasoning** | Gemini via LangGraph | Narrative, comparison, briefing structure |
| **Policy reasoning** | Guardrail nodes | Refuse unsupported speculative claims |

**Reasoning policy (constitution excerpts):**
- Prefer numbers from tools over model priors  
- Use uncertainty language when intervals exist  
- Separate “model predicts” from “reported incidents”  
- Never recommend illegal or extrajudicial action  
- Patrol suggestions are **recommendations**, require human approval API  

---

## 8. Prompt engineering

### 8.1 Prompt stack (layered)

| Layer | Name | Contents |
|-------|------|----------|
| L0 | **Constitution** | LEA ethics, no speculation, citation mandate, AuthZ respect |
| L1 | **Role overlay** | Tone/detail for SP vs analyst vs control room |
| L2 | **Mode template** | ask / brief / explain section structure |
| L3 | **Tool catalog digest** | Short descriptions of allowed tools |
| L4 | **Context pack** | Compressed evidence |
| L5 | **User utterance** | Current question |

### 8.2 Output contracts

**Ask mode:**
1. Direct answer (≤ N paragraphs)  
2. Evidence bullets with citation ids  
3. Caveats / data gaps  
4. Suggested follow-ups  

**Brief mode:**
1. Situation overview  
2. Hotspots & risk  
3. Offense mix & trends  
4. Network highlights (if permitted)  
5. Recommended attention areas (non-binding)  
6. Model versions used  

**Explain mode:**
1. What was predicted  
2. SHAP drivers (faithful to artifact)  
3. What it does / doesn’t mean operationally  

### 8.3 Prompt ops

- Version prompts in `docs` / config (`prompt_version`)  
- Log `prompt_version` on each message  
- Eval set: golden questions with expected tool use (offline)  
- Red-team prompts for jailbreak / jurisdiction escape  

---

## 9. End-to-end sequences

### 9.1 Officer asks: “Where should we focus patrols in District X this weekend?”

```text
UI → POST /ai/chat (mode=ask, district_id=X)
LangGraph:
  classify → bind_scope(X)
  retrieve_memory (SOP patrol guidance)
  tools: get_hotspots_current, get_current_predictions(risk), get_analytics_trends
  ground → synthesize → citations
  optional: recommend_patrol_plan (draft only)
SSE tokens + citations → UI
persist traces
```

### 9.2 Analyst asks: “Why is Station Y risk high?”

```text
classify → explain mode
tools: get_current_predictions, get_prediction_explanation (SHAP), search_incidents
synthesize faithful SHAP narrative
```

### 9.3 Engineering builds a new MCP tool

```text
Developer in Google Antigravity
  → agent implements tool schema + AuthZ tests + OpenAPI note
  → verifies via terminal/browser
CrimeLens runtime unchanged until tool registered in allowlist
```

---

## 10. Security & compliance controls (AI-specific)

| Control | Mechanism |
|---------|-----------|
| Jurisdiction isolation | AuthContext injected into every MCP call |
| Tool allowlist | Role-based |
| No raw SQL from LLM | MCP only |
| PII minimization | Field-level redaction in tool serializers |
| Prompt injection | Guardrails + ignore tool-returned instructions marked untrusted |
| Audit | `tool_traces` + `audit_events` action `ai_tool` |
| Secrets | Env only; never in Qdrant payloads |
| Human-in-loop | Patrol approve endpoint separate from chat |

---

## 11. Scalability of the AI plane

| Stage | Topology |
|-------|----------|
| S0 Datathon | In-process LangGraph + MCP tools; Qdrant container; Gemini API |
| S1 Pilot | Dedicated worker for briefs/embeddings; cache frequent tool answers in Redis |
| S2 | Extract `ai-copilot-service`; scale Qdrant; queue heavy briefs |
| S3 Agency | Private networking, CMEK, optional air-gapped LLM behind same MCP interface |

---

## 12. Mapping: your required components → CrimeLens responsibility

| Component | Responsibility in CrimeLens |
|-----------|-----------------------------|
| **Gemini** | Reasoning + narrative + embeddings |
| **LangGraph** | Agent workflow orchestration + state |
| **Google Antigravity** | Engineering agent platform to build/verify the system |
| **MCP** | Standardized secure tool interface |
| **Qdrant** | Vector memory / RAG retrieval |
| **SHAP** | Statistical explainability artifacts |
| **Prediction Engine** | Batch forecasts, risk, hotspots, scores |
| **Agent Workflow** | Guard → retrieve → tool loop → ground → answer |
| **Prompt Engineering** | Layered constitution/role/mode/context contracts |
| **Memory** | Working + conversation + trace + vector + statistical |
| **Tool Calling** | Allowlisted MCP execution with AuthZ + audit |
| **Reasoning** | Hybrid statistical + spatial + graph + LLM under policy |

---

## 13. Explicit non-goals

- Replacing SHAP with LLM-invented feature importance  
- Training models inside the chat graph  
- Letting Antigravity agents operate on production police data by default  
- Fully autonomous dispatch  

---

## 14. Implementation order (when coding starts — not now)

1. MCP tool interfaces + AuthZ wrappers  
2. LangGraph minimal ask graph + SSE  
3. Prediction/SHAP read tools  
4. Qdrant embed/upsert worker + rag tool  
5. Brief mode + Pro routing  
6. Eval harness + prompt versions  
7. Antigravity used by eng team for delivery acceleration  

---

## Approval gate

Confirm especially:

1. **LangGraph** as production orchestrator (vs PydanticAI-only)  
2. **Qdrant** as target RAG store (pgvector optional bootstrap)  
3. **Antigravity** limited to engineering plane (not officer chat runtime)  
4. Prediction Engine / SHAP remain non-LLM statistical plane  

**STOP — awaiting approval before next design phase.**
