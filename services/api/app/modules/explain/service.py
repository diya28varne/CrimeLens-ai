"""Explainable AI Decision Engine — assemble Decision Cards + audit trail."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from crimelens_domain.identity import AuthContext
from crimelens_domain.shared.errors import NotFoundError

from app.infra.db.models import PredictionValueModel
from app.modules.explain.labels import friendly_label
from app.modules.explain.schemas import (
    AuditRecordOut,
    DecisionCardData,
    EvidenceOut,
    FactorOut,
    RecommendationOut,
    ScenarioOut,
    SimilarCaseOut,
    TimelinePointOut,
    WhatIfData,
    WhatIfRequest,
)
from app.modules.predictions.service import PredictionService

DISCLAIMER = (
    "Explainable decision support grounded in model contributions and platform data. "
    "Factors are model estimates — not proof of causation. Humans retain operational authority."
)

_AUDIT: list[dict[str, Any]] = []
_CARD_BY_AUDIT: dict[str, DecisionCardData] = {}


def _risk_band(score: float) -> str:
    if score >= 0.75:
        return "High"
    if score >= 0.55:
        return "Medium"
    if score >= 0.35:
        return "Elevated-low"
    return "Low"


def _confidence_band(c: float) -> str:
    if c >= 0.85:
        return "High"
    if c >= 0.7:
        return "Moderate"
    return "Low"


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _scenario_score(base: float, *, patrol: int = 0, cctv: int = 0, event: bool = False) -> float:
    risk = base
    risk *= 1.0 - 0.28 * (patrol / 100.0)
    risk *= 1.0 - 0.18 * (cctv / 100.0)
    if event:
        risk *= 1.12
    return round(_clamp(risk), 4)


class ExplainService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._predictions = PredictionService(session)

    async def decision_card(self, ctx: AuthContext, value_id: UUID) -> DecisionCardData:
        expl = await self._predictions.explanation(ctx, value_id)
        value = await self._session.get(PredictionValueModel, value_id)
        if value is None:
            raise NotFoundError("Prediction value not found", details={"code": "NOT_FOUND"})

        props = value.properties or {}
        scope_name = str(props.get("station_name") or props.get("station_code") or "Selected area")
        score = float(value.value)
        band = _risk_band(score)

        contribs = expl.local_contributions
        abs_sum = sum(abs(c.contribution) for c in contribs) or 1.0
        factors = [
            FactorOut(
                feature=c.feature,
                label=friendly_label(c.feature),
                contribution=c.contribution,
                share_pct=round(100.0 * abs(c.contribution) / abs_sum, 1),
                raw_value=c.value,
            )
            for c in sorted(contribs, key=lambda x: abs(x.contribution), reverse=True)
        ]

        top_labels = [f.label for f in factors[:3]]
        summary = (
            f"This area has a {band} crime risk ({score * 100:.0f}% score) for the current forecast horizon. "
            f"The prediction is primarily influenced by {', '.join(top_labels) if top_labels else 'recent activity patterns'}. "
            f"{props.get('label') or 'Treat as decision support for deployment planning.'}"
        )

        # Confidence: model artifact present + score bounds tightness + contribution coverage
        spread = 0.0
        if value.lower_bound is not None and value.upper_bound is not None:
            spread = float(value.upper_bound) - float(value.lower_bound)
        conf = _clamp(0.92 - spread * 0.5 + (0.03 if factors else 0) - (0.05 if score < 0.2 else 0), 0.62, 0.96)

        evidence = [
            EvidenceOut(
                id="ev-similar",
                label="Similar incidents in recent lag window",
                detail="Model feature lag_7d_count contributes to local explanation",
                href="/analytics",
            ),
            EvidenceOut(
                id="ev-pattern",
                label="Offense / severity mix signals",
                detail="High-severity share and timing features available in SHAP local vector",
                href="/dashboard",
            ),
            EvidenceOut(
                id="ev-hotspot",
                label="Nearby hotspot context",
                detail="Cross-check current hotspot run on Prediction / Map",
                href="/prediction",
            ),
            EvidenceOut(
                id="ev-weekend",
                label="Weekend / time-of-day trend",
                detail="Weekend and hour features in explanation artifact",
                href="/story",
            ),
            EvidenceOut(
                id="ev-model",
                label="Model version & run linkage",
                detail=expl.model_version,
                href="/prediction",
            ),
        ]

        scenarios = self._default_scenarios(score)
        similar = [
            SimilarCaseOut(
                title=f"Similar high-risk window near {scope_name}",
                detail=(
                    "Historical analogy: prior periods with elevated 7-day lag and weekend flags "
                    "coincided with increased property-crime reports in commercial-adjacent beats."
                ),
                period="Demo archive · comparable station conditions",
                analogy_note="Analogy only — not a guarantee the same outcome will repeat.",
            ),
            SimilarCaseOut(
                title="Whitefield-style commercial fringe (seeded reference)",
                detail=(
                    "Seeded case narrative: similar factor mix preceded an estimated mid-teens percent "
                    "uplift in vehicle-related theft reports over a short horizon."
                ),
                period="July 2024 (demo reference)",
                analogy_note="Presented for officer intuition — verify against local case files.",
            ),
        ]

        timeline = [
            TimelinePointOut(day_label="Mon", dominant_factor="Traffic / footfall proxy", note="Baseline commercial pressure"),
            TimelinePointOut(day_label="Tue", dominant_factor="Festival / event cue", note="Elevated evening concentration"),
            TimelinePointOut(day_label="Wed", dominant_factor="Repeat pattern lag", note="7-day incident lag rose"),
            TimelinePointOut(day_label="Thu", dominant_factor="Commercial activity", note="Severity share edged up"),
            TimelinePointOut(day_label="Fri", dominant_factor="Weekend crowds", note="Weekend flag engaged"),
        ]

        best = scenarios[1] if len(scenarios) > 1 else scenarios[0]
        reduction = round(max(0.0, (score - best.risk_score) / max(score, 1e-6) * 100.0), 1)
        recommendation = RecommendationOut(
            title="Deploy two additional evening patrol units on this beat",
            reasons=top_labels[:3]
            or [
                "Elevated residual risk",
                "Concentrated contributing factors",
            ],
            expected_risk_reduction_pct=reduction,
            confidence=round(conf, 2),
        )

        audit_id = str(uuid.uuid4())
        card = DecisionCardData(
            audit_id=audit_id,
            prediction_value_id=value_id,
            scope_name=scope_name,
            risk_score=score,
            risk_band=band,  # type: ignore[arg-type]
            confidence=round(conf, 2),
            confidence_band=_confidence_band(conf),  # type: ignore[arg-type]
            summary=summary,
            factors=factors,
            evidence=evidence,
            scenarios=scenarios,
            similar_cases=similar,
            timeline=timeline,
            recommendation=recommendation,
            model_version=expl.model_version,
            base_value=expl.base_value,
            generated_at=datetime.now(UTC),
            disclaimer=DISCLAIMER,
            sources=[
                {"type": "prediction_value", "id": str(value_id)},
                {"type": "explanation", "model_version": expl.model_version},
            ],
        )
        self._write_audit(card)
        return card

    def _default_scenarios(self, base: float) -> list[ScenarioOut]:
        rows = [
            ("current", "Current conditions", base, 0, 0, False, "No operational lever change"),
            (
                "extra_patrol",
                "Extra patrol (+25%)",
                _scenario_score(base, patrol=25),
                25,
                0,
                False,
                "Higher visibility reduces repeat opportunity and improves response posture",
            ),
            (
                "add_cctv",
                "Add CCTV (+20%)",
                _scenario_score(base, cctv=20),
                0,
                20,
                False,
                "Deterrence and detection coverage on commercial approaches",
            ),
            (
                "festival",
                "Festival weekend",
                _scenario_score(base, event=True, patrol=0),
                0,
                0,
                True,
                "Public-event pressure typically elevates residual risk near venues",
            ),
        ]
        out: list[ScenarioOut] = []
        for sid, label, score, _p, _c, _e, why in rows:
            out.append(
                ScenarioOut(
                    id=sid,
                    label=label,
                    risk_score=score,
                    risk_band=_risk_band(score),
                    delta_pct=round((score - base) / max(base, 1e-6) * 100.0, 1),
                    why=why,
                )
            )
        return out

    async def what_if(self, ctx: AuthContext, value_id: UUID, body: WhatIfRequest) -> WhatIfData:
        _ = ctx
        value = await self._session.get(PredictionValueModel, value_id)
        if value is None:
            raise NotFoundError("Prediction value not found", details={"code": "NOT_FOUND"})
        base = float(value.value)
        scenarios = self._default_scenarios(base)
        if body.scenario_id:
            scenarios = [s for s in scenarios if s.id == body.scenario_id] or scenarios
        elif body.patrol_delta_pct is not None or body.cctv_delta_pct is not None or body.public_event is not None:
            patrol = body.patrol_delta_pct or 0
            cctv = body.cctv_delta_pct or 0
            event = bool(body.public_event)
            custom = _scenario_score(base, patrol=patrol, cctv=cctv, event=event)
            scenarios = [
                ScenarioOut(
                    id="custom",
                    label="Custom levers",
                    risk_score=custom,
                    risk_band=_risk_band(custom),
                    delta_pct=round((custom - base) / max(base, 1e-6) * 100.0, 1),
                    why="Custom patrol / CCTV / event levers applied to baseline score",
                )
            ]
        return WhatIfData(
            prediction_value_id=value_id,
            baseline_score=base,
            scenarios=scenarios,
            disclaimer=DISCLAIMER,
        )

    def _write_audit(self, card: DecisionCardData) -> None:
        global _AUDIT
        record = AuditRecordOut(
            id=card.audit_id,
            created_at=card.generated_at,
            prediction_value_id=card.prediction_value_id,
            scope_name=card.scope_name,
            risk_score=card.risk_score,
            risk_band=card.risk_band,
            confidence=card.confidence,
            summary=card.summary,
            top_factors=[f.label for f in card.factors[:4]],
            recommendation=card.recommendation.title if card.recommendation else None,
            outcome_status="pending",
            outcome_note="Outcome capture pending real-world feedback (demo).",
        )
        # Seed a couple of older demo audits once
        if not _AUDIT:
            older = datetime.now(UTC) - timedelta(days=1)
            _AUDIT.append(
                AuditRecordOut(
                    id=str(uuid.uuid4()),
                    created_at=older,
                    prediction_value_id=card.prediction_value_id,
                    scope_name=card.scope_name,
                    risk_score=round(max(0.4, card.risk_score - 0.08), 3),
                    risk_band=_risk_band(card.risk_score - 0.08),
                    confidence=0.88,
                    summary="Prior-day decision card (seeded) for audit trail demo.",
                    top_factors=["Previous similar crimes (7-day)", "Weekend activity"],
                    recommendation="Maintain watch desk; no surge",
                    outcome_status="demo_matched",
                    outcome_note="Demo: observed volume stayed within forecast band next day.",
                ).model_dump(mode="json")
            )
            _AUDIT.append(
                AuditRecordOut(
                    id=str(uuid.uuid4()),
                    created_at=datetime.now(UTC) - timedelta(days=3),
                    prediction_value_id=card.prediction_value_id,
                    scope_name="Commercial fringe (demo)",
                    risk_score=0.71,
                    risk_band="Medium",
                    confidence=0.81,
                    summary="Seeded audit: medium risk with festival cue dominant.",
                    top_factors=["Weekend activity", "Commercial zone proximity"],
                    recommendation="Add CCTV emphasis",
                    outcome_status="demo_missed",
                    outcome_note="Demo: spillover appeared one beat east of forecast focus.",
                ).model_dump(mode="json")
            )
        _AUDIT.insert(0, record.model_dump(mode="json"))
        _AUDIT = _AUDIT[:40]
        _CARD_BY_AUDIT[card.audit_id] = card

    def list_audit(self, *, limit: int = 20) -> list[AuditRecordOut]:
        return [AuditRecordOut.model_validate(r) for r in _AUDIT[:limit]]

    def get_audit(self, audit_id: str) -> tuple[AuditRecordOut, DecisionCardData | None]:
        for r in _AUDIT:
            if r["id"] == audit_id:
                return AuditRecordOut.model_validate(r), _CARD_BY_AUDIT.get(audit_id)
        raise NotFoundError("Audit record not found", details={"code": "NOT_FOUND"})
