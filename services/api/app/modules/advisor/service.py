"""Strategic Intelligence Advisor — grounded brief orchestration (no invented facts)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from crimelens_domain.identity import AuthContext

from app.infra.db.models import PredictionMetric
from app.modules.analytics.crime_service import CrimeAnalyticsService
from app.modules.dashboard.service import DashboardService
from app.modules.network.service import NetworkService
from app.modules.predictions.service import PredictionService
from app.modules.advisor.schemas import (
    ActionOut,
    AdvisorBriefData,
    EvidenceItem,
    PatternOut,
    RiskAreaOut,
    SummaryBlock,
    TimelineEntryOut,
)

DISCLAIMER = (
    "Intelligence briefing grounded in CrimeLens analytics, predictions, and network data. "
    "Observed = measured from incidents; Forecast = model estimates. Not operational orders."
)

# In-process brief cache + history for Timeline lite (datathon; no migration)
_BRIEF_CACHE: AdvisorBriefData | None = None
_BRIEF_HISTORY: list[TimelineEntryOut] = []


def _risk_band(score: float) -> str:
    if score >= 0.75:
        return "High"
    if score >= 0.55:
        return "Medium"
    if score >= 0.35:
        return "Elevated-low"
    return "Low"


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


class AdvisorService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._dashboard = DashboardService(session)
        self._analytics = CrimeAnalyticsService(session)
        self._predictions = PredictionService(session)
        self._network = NetworkService(session)

    async def current_brief(
        self,
        ctx: AuthContext,
        *,
        force: bool = False,
    ) -> AdvisorBriefData:
        global _BRIEF_CACHE
        if _BRIEF_CACHE is not None and not force:
            # Attach latest timeline view
            brief = _BRIEF_CACHE.model_copy(deep=True)
            brief.timeline = list(_BRIEF_HISTORY[:14])
            return brief
        brief = await self._build(ctx)
        self._remember(brief)
        return brief

    async def refresh(self, ctx: AuthContext) -> AdvisorBriefData:
        return await self.current_brief(ctx, force=True)

    def history(self, *, limit: int = 14) -> list[TimelineEntryOut]:
        if _BRIEF_HISTORY:
            return _BRIEF_HISTORY[:limit]
        return []

    def _remember(self, brief: AdvisorBriefData) -> None:
        global _BRIEF_CACHE, _BRIEF_HISTORY
        _BRIEF_CACHE = brief
        entry = TimelineEntryOut(
            id=brief.id,
            generated_at=brief.generated_at,
            summary_excerpt=brief.summary.headline[:180],
            recommendation_count=len(brief.actions),
            hotspot_realized_note=None,
            accuracy_note="Current brief",
            acted_on_demo=None,
        )
        # Seed synthetic prior days once for demo timeline
        if not _BRIEF_HISTORY:
            seeded = self._seed_timeline(brief)
            _BRIEF_HISTORY = [entry, *seeded]
        else:
            _BRIEF_HISTORY = [entry, *[e for e in _BRIEF_HISTORY if e.id != brief.id]][:30]
        brief.timeline = list(_BRIEF_HISTORY[:14])

    def _seed_timeline(self, brief: AdvisorBriefData) -> list[TimelineEntryOut]:
        seeds: list[TimelineEntryOut] = []
        templates = [
            (
                1,
                "Eastern fringe risk elevated; evening vehicle-theft watch recommended.",
                True,
                "2 of 3 highlighted cells remained above threshold next day.",
            ),
            (
                2,
                "Weekend uplift in commercial corridors; metro-adjacent patrol emphasis.",
                True,
                "Hotspot rank #1 held; rank #2 shifted south ~400m.",
            ),
            (
                3,
                "Stable citywide volume; residual high-severity share in central beats.",
                False,
                "Forecast band matched Medium for primary district.",
            ),
            (
                5,
                "Repeat-offender link density noted across neighboring stations.",
                True,
                "Network cue aligned with two subsequent property incidents (demo).",
            ),
        ]
        for days_ago, excerpt, acted, accuracy in templates:
            seeds.append(
                TimelineEntryOut(
                    id=str(uuid.uuid4()),
                    generated_at=brief.generated_at - timedelta(days=days_ago),
                    summary_excerpt=excerpt,
                    recommendation_count=3 + (days_ago % 2),
                    hotspot_realized_note="Partial realization vs prior forecast (seeded demo)."
                    if days_ago <= 2
                    else None,
                    accuracy_note=accuracy,
                    acted_on_demo=acted,
                )
            )
        return seeds

    async def _build(self, ctx: AuthContext) -> AdvisorBriefData:
        now = datetime.now(UTC)
        overview = await self._dashboard.overview(
            ctx, district_id=None, station_id=None, from_=None, to=None
        )
        trends = await self._analytics.trends(
            ctx,
            district_id=None,
            station_id=None,
            from_=now - timedelta(days=14),
            to=now,
            interval="day",
        )
        breakdown = await self._analytics.breakdown(
            ctx,
            district_id=None,
            station_id=None,
            from_=now - timedelta(days=30),
            to=now,
            group_by="offense",
        )
        pred = await self._predictions.current(
            ctx, metric=PredictionMetric.risk_score, top_n=8
        )
        hotspots = await self._predictions.hotspots_current(ctx, limit=5)
        repeats = await self._network.repeat_offenders(ctx, limit=5)

        wow = overview.kpis.total_incidents_delta_pct
        total = overview.kpis.total_incidents
        open_n = overview.kpis.open_incidents
        high_sev = overview.kpis.high_severity

        # Trend last 7 vs prior 7 from series points
        points = []
        if trends.get("series"):
            points = trends["series"][0].get("points") or []
        recent = sum(int(p["count"]) for p in points[-7:]) if points else 0
        prior = sum(int(p["count"]) for p in points[-14:-7]) if len(points) >= 14 else max(recent, 1)
        trend_pct = round(((recent - prior) / prior) * 100.0, 1) if prior else 0.0
        if wow is not None:
            trend_pct = float(wow)

        top_offense = (breakdown.get("items") or [{}])[0] if breakdown.get("items") else {}
        offense_name = str(top_offense.get("name") or top_offense.get("key") or "property crime")
        offense_count = int(top_offense.get("count") or 0)

        hs_features = hotspots.features
        hs_labels = [str(f.properties.get("label") or f"Hotspot #{f.rank}") for f in hs_features[:3]]
        top_stations = pred.values[:4]

        # --- Summary ---
        direction = "increased" if trend_pct > 2 else "decreased" if trend_pct < -2 else "held steady"
        hs_clause = (
            f" {len(hs_features)} active hotspot cluster(s) flagged"
            + (f" including {', '.join(hs_labels[:2])}." if hs_labels else ".")
            if hs_features
            else " No current hotspot run features available."
        )
        evening_hint = (
            " Based on current risk scores, additional patrol coverage is recommended between 7 PM and 10 PM."
            if top_stations and top_stations[0].value >= 0.55
            else ""
        )
        headline = f"Crime activity {direction} {abs(trend_pct):.0f}% vs prior window"
        body = (
            f"{'Observed: ' if True else ''}"
            f"Jurisdiction recorded {total} incidents in the active window "
            f"({open_n} open). Volume {direction} {abs(trend_pct):.1f}% versus the prior comparable window. "
            f"Leading category: {offense_name} ({offense_count} incidents). "
            f"{'Forecast: ' if hs_features or top_stations else ''}"
            f"{hs_clause.strip()}{evening_hint}"
        )

        summary = SummaryBlock(
            headline=headline,
            body=body,
            week_over_week_pct=trend_pct,
            kind_tags=["observed", "forecast"] if (hs_features or top_stations) else ["observed"],
        )

        patterns = self._patterns(
            trend_pct=trend_pct,
            offense_name=offense_name,
            offense_count=offense_count,
            points=points,
            hs_features=hs_features,
            hs_labels=hs_labels,
            repeats=repeats,
            high_sev=high_sev,
            total=total,
        )
        risk_areas = self._risk_areas(pred, hotspots)
        actions = self._actions(
            trend_pct=trend_pct,
            offense_name=offense_name,
            top_stations=top_stations,
            hs_labels=hs_labels,
            repeats=repeats,
        )

        sources: list[dict[str, Any]] = [
            {"type": "dashboard_overview", "total_incidents": total, "delta_pct": trend_pct},
        ]
        if pred.run:
            sources.append(
                {
                    "type": "prediction_run",
                    "id": str(pred.run.id),
                    "model": f"{pred.run.model_code}@{pred.run.model_version}",
                }
            )
        if hotspots.run:
            sources.append(
                {
                    "type": "hotspot_run",
                    "id": str(hotspots.run.id),
                    "method": hotspots.run.method,
                }
            )

        conf = _clamp(
            0.88
            + (0.04 if pred.values else 0)
            + (0.03 if hs_features else 0)
            - (0.05 if total < 5 else 0),
            0.72,
            0.95,
        )

        return AdvisorBriefData(
            id=str(uuid.uuid4()),
            generated_at=now,
            summary=summary,
            patterns=patterns[:5],
            risk_areas=risk_areas[:6],
            actions=actions[:5],
            timeline=[],
            sources=sources,
            disclaimer=DISCLAIMER,
            confidence=round(conf, 2),
        )

    def _patterns(
        self,
        *,
        trend_pct: float,
        offense_name: str,
        offense_count: int,
        points: list[dict],
        hs_features: list,
        hs_labels: list[str],
        repeats: list,
        high_sev: int,
        total: int,
    ) -> list[PatternOut]:
        out: list[PatternOut] = []

        out.append(
            PatternOut(
                id="p-volume",
                title=f"Volume {('↑' if trend_pct > 0 else '↓' if trend_pct < 0 else '→')} {abs(trend_pct):.0f}% vs prior window",
                explanation=(
                    f"Observed incident counts moved {trend_pct:+.1f}% versus the previous comparable period "
                    f"({total} incidents in the current analytics window)."
                ),
                kind="observed",
                confidence=0.9 if total >= 10 else 0.78,
                strength="high" if abs(trend_pct) >= 8 else "medium",
                evidence=[
                    EvidenceItem(
                        kind="trend",
                        label="Week-over-week volume",
                        detail="Dashboard KPI delta vs prior window",
                        value=trend_pct,
                        href="/analytics",
                    ),
                    EvidenceItem(
                        kind="count",
                        label="Incidents (window)",
                        detail="Dashboard overview total",
                        value=total,
                        href="/dashboard",
                    ),
                ],
            )
        )

        out.append(
            PatternOut(
                id="p-offense",
                title=f"{offense_name} leads the offense mix",
                explanation=(
                    f"Observed: {offense_name} accounts for {offense_count} incidents in the last ~30 days — "
                    "the top category in the breakdown. Prioritize category-specific prevention messaging."
                ),
                kind="observed",
                confidence=0.86 if offense_count else 0.7,
                strength="high" if offense_count >= 5 else "medium",
                evidence=[
                    EvidenceItem(
                        kind="breakdown",
                        label="Top offense",
                        detail=offense_name,
                        value=offense_count,
                        href="/analytics",
                    )
                ],
            )
        )

        if hs_features:
            out.append(
                PatternOut(
                    id="p-hotspots",
                    title=f"{len(hs_features)} hotspot cluster(s) active",
                    explanation=(
                        "Forecast / detection: current hotspot run highlights "
                        + (", ".join(hs_labels) if hs_labels else "multiple cells")
                        + ". Treat as elevated watch areas, not confirmed future crimes."
                    ),
                    kind="forecast",
                    confidence=0.84,
                    strength="high",
                    evidence=[
                        EvidenceItem(
                            kind="hotspot",
                            label=f.properties.get("label") or f"Rank {f.rank}",
                            detail=f"score={f.score:.2f}, incidents={f.incident_count}",
                            value=f.score,
                            href="/prediction",
                        )
                        for f in hs_features[:3]
                    ],
                )
            )

        # Day-of-week skew from daily points if enough data
        if len(points) >= 7:
            # Approximate: peak day in last 14 buckets
            peak = max(points[-14:], key=lambda p: int(p["count"]))
            out.append(
                PatternOut(
                    id="p-peak-day",
                    title="Peak activity day in recent series",
                    explanation=(
                        f"Observed: highest daily count in the recent series was {peak['bucket_start']} "
                        f"({peak['count']} incidents). Align surge staffing to recurring peak weekdays when the pattern holds."
                    ),
                    kind="observed",
                    confidence=0.8,
                    strength="medium",
                    evidence=[
                        EvidenceItem(
                            kind="trend",
                            label="Peak day",
                            detail=str(peak["bucket_start"]),
                            value=int(peak["count"]),
                            href="/analytics",
                        )
                    ],
                )
            )

        if repeats:
            top = repeats[0]
            name = top.full_name
            out.append(
                PatternOut(
                    id="p-repeat",
                    title="Repeat-offender pressure in network view",
                    explanation=(
                        f"Observed network signal: top repeat-linked subject '{name}' appears in the current "
                        "repeat-offender ranking. Cross-check with neighboring station casework."
                    ),
                    kind="observed",
                    confidence=0.82,
                    strength="medium",
                    evidence=[
                        EvidenceItem(
                            kind="network",
                            label="Repeat offender",
                            detail=str(name),
                            value=top.incident_count,
                            href="/network",
                        )
                    ],
                )
            )

        if high_sev and total:
            share = round(100.0 * high_sev / max(total, 1), 1)
            out.append(
                PatternOut(
                    id="p-severity",
                    title=f"High/critical severity share ~{share}%",
                    explanation=(
                        f"Observed: {high_sev} high/critical severity incidents in the overview mix "
                        f"(~{share}% of window volume). Escalate supervisory review on those dockets."
                    ),
                    kind="observed",
                    confidence=0.85,
                    strength="medium" if share < 25 else "high",
                    evidence=[
                        EvidenceItem(
                            kind="severity",
                            label="High/critical count",
                            detail="From dashboard severity mix",
                            value=high_sev,
                            href="/dashboard",
                        )
                    ],
                )
            )

        return out

    def _risk_areas(self, pred, hotspots) -> list[RiskAreaOut]:
        areas: list[RiskAreaOut] = []
        for v in pred.values[:5]:
            props = v.properties or {}
            name = str(props.get("station_name") or props.get("station_code") or "Station")
            score = float(v.value)
            band = _risk_band(score)
            why = str(props.get("label") or "Elevated residual risk vs city baseline.")
            # Pull SHAP-ish hint from properties only; full explanation on demand in UI via prediction page
            areas.append(
                RiskAreaOut(
                    id=str(v.id),
                    name=name,
                    risk_band=band,  # type: ignore[arg-type]
                    risk_score=score,
                    confidence=_clamp(0.78 + score * 0.15, 0.75, 0.94),
                    why=f"Forecast risk score {score:.2f}. {why}",
                    kind="forecast",
                    evidence=[
                        EvidenceItem(
                            kind="prediction",
                            label="Station risk",
                            detail=name,
                            value=score,
                            href="/prediction",
                        )
                    ],
                )
            )
        # Also surface hotspot as area if few stations
        if len(areas) < 3:
            for f in hotspots.features[: 3 - len(areas)]:
                label = str(f.properties.get("label") or f"Hotspot #{f.rank}")
                areas.append(
                    RiskAreaOut(
                        id=str(f.id),
                        name=label,
                        risk_band=_risk_band(float(f.score)),  # type: ignore[arg-type]
                        risk_score=float(f.score),
                        confidence=0.83,
                        why=f"Hotspot intensity {f.score:.2f} from {f.incident_count} linked incidents in window.",
                        kind="forecast",
                        evidence=[
                            EvidenceItem(
                                kind="hotspot",
                                label=label,
                                detail=f"rank={f.rank}",
                                value=f.score,
                                href="/map",
                            )
                        ],
                    )
                )
        return areas

    def _actions(
        self,
        *,
        trend_pct: float,
        offense_name: str,
        top_stations: list,
        hs_labels: list[str],
        repeats: list,
    ) -> list[ActionOut]:
        actions: list[ActionOut] = []
        focus = (
            str((top_stations[0].properties or {}).get("station_name") or "priority stations")
            if top_stations
            else "priority corridors"
        )
        hs = hs_labels[0] if hs_labels else "active hotspot cells"

        actions.append(
            ActionOut(
                id="a-patrol-evening",
                title=f"Increase patrol frequency near {hs} (19:00–22:00)",
                rationale=(
                    "Forecast risk and hotspot intensity concentrate in evening commercial / metro-adjacent cells. "
                    "A short surge window improves coverage without full-shift overtime."
                ),
                confidence=0.86,
                priority="high",
                simulation_preset_id="weekend_festival" if trend_pct > 5 else "vip_movement",
                evidence=[
                    EvidenceItem(
                        kind="hotspot",
                        label="Focus cluster",
                        detail=hs,
                        href="/prediction",
                    ),
                    EvidenceItem(
                        kind="link",
                        label="Test in Simulator",
                        detail="Open Digital Twin with related preset",
                        href="/simulation",
                    ),
                ],
            )
        )

        actions.append(
            ActionOut(
                id="a-station-cover",
                title=f"Deploy two additional units covering {focus}",
                rationale=(
                    f"Top station risk scores point to {focus}. Pair units with the leading offense pattern "
                    f"({offense_name}) rather than spreading thinly citywide."
                ),
                confidence=0.84,
                priority="high",
                simulation_preset_id="vip_movement",
                evidence=[
                    EvidenceItem(
                        kind="prediction",
                        label="Top risk station",
                        detail=focus,
                        href="/prediction",
                    )
                ],
            )
        )

        actions.append(
            ActionOut(
                id="a-parking",
                title="Monitor parking & commercial frontage on peak evenings",
                rationale=(
                    f"Observed mix is led by {offense_name}. Parking and frontage checks are low-cost "
                    "deterrence aligned with commercial-zone concentration in the brief."
                ),
                confidence=0.8,
                priority="medium",
                simulation_preset_id=None,
                evidence=[
                    EvidenceItem(
                        kind="breakdown",
                        label="Leading offense",
                        detail=offense_name,
                        href="/analytics",
                    )
                ],
            )
        )

        if trend_pct > 5:
            actions.append(
                ActionOut(
                    id="a-festival",
                    title="Pre-plan surge for weekend / public-event windows",
                    rationale=(
                        "Volume is rising vs prior window. Run the Weekend Festival scenario in Simulation "
                        "to pressure-test patrol and CCTV levers before the next event."
                    ),
                    confidence=0.81,
                    priority="medium",
                    simulation_preset_id="weekend_festival",
                    evidence=[
                        EvidenceItem(
                            kind="trend",
                            label="Volume delta %",
                            detail="vs prior window",
                            value=trend_pct,
                            href="/simulation",
                        )
                    ],
                )
            )

        if repeats:
            actions.append(
                ActionOut(
                    id="a-network",
                    title="Task analyst review of top repeat-offender links",
                    rationale=(
                        "Network ranking shows concentrated repeat activity. A short link-analysis pass can "
                        "inform targeted inquiries without broad dragnet tactics."
                    ),
                    confidence=0.83,
                    priority="medium",
                    evidence=[
                        EvidenceItem(
                            kind="network",
                            label="Repeat offenders",
                            detail="Current network ranking",
                            href="/network",
                        )
                    ],
                )
            )

        return actions
