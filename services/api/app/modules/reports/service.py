"""One-click Executive Intelligence Report orchestrator."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from crimelens_domain.identity import AuthContext

from app.infra.db.models import PredictionMetric
from app.modules.advisor.service import AdvisorService
from app.modules.analytics.crime_service import CrimeAnalyticsService
from app.modules.dashboard.service import DashboardService
from app.modules.explain.service import ExplainService
from app.modules.predictions.service import PredictionService
from app.modules.reports.schemas import (
    ChecklistItemOut,
    CoverOut,
    GenerateReportRequest,
    HotspotOut,
    InsightOut,
    IntelligenceReportData,
    OverviewOut,
    PredictionOut,
    PresenterSlideOut,
    RecommendationOut,
    ReportTemplateOut,
    ResourcePlanOut,
    XaiSummaryOut,
)

DISCLAIMER = (
    "Intelligence report assembled from CrimeLens analytics, predictions, and explanations. "
    "Observed = measured incidents; Forecast = model estimates. Not an operational order."
)

TEMPLATES: list[ReportTemplateOut] = [
    ReportTemplateOut(
        id="daily",
        name="Daily Intelligence Brief",
        description="Compact overnight-to-morning pack for command standup.",
        default_days=1,
    ),
    ReportTemplateOut(
        id="weekly",
        name="Weekly Crime Analysis",
        description="Default executive briefing with trends, hotspots, and actions.",
        default_days=7,
    ),
    ReportTemplateOut(
        id="festival",
        name="Festival Security Assessment",
        description="Event-oriented brief with elevated crowd / commercial risk cues.",
        default_days=14,
    ),
]

_REPORT_CACHE: dict[str, IntelligenceReportData] = {}


def _risk_band(score: float) -> str:
    if score >= 0.75:
        return "High"
    if score >= 0.55:
        return "Medium"
    if score >= 0.35:
        return "Elevated-low"
    return "Low"


class ReportsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._dashboard = DashboardService(session)
        self._analytics = CrimeAnalyticsService(session)
        self._predictions = PredictionService(session)
        self._advisor = AdvisorService(session)
        self._explain = ExplainService(session)

    def list_templates(self) -> list[ReportTemplateOut]:
        return list(TEMPLATES)

    def get_cached(self, report_id: str) -> IntelligenceReportData | None:
        return _REPORT_CACHE.get(report_id)

    async def generate(self, ctx: AuthContext, body: GenerateReportRequest) -> IntelligenceReportData:
        tmpl = next((t for t in TEMPLATES if t.id == body.template_id), TEMPLATES[1])
        now = datetime.now(UTC)
        to_d = body.to or now.date()
        from_d = body.from_ or (to_d - timedelta(days=tmpl.default_days))
        from_dt = datetime.combine(from_d, datetime.min.time(), tzinfo=UTC)
        to_dt = datetime.combine(to_d + timedelta(days=1), datetime.min.time(), tzinfo=UTC)

        overview = await self._dashboard.overview(
            ctx,
            district_id=body.district_id,
            station_id=None,
            from_=from_dt,
            to=to_dt,
        )
        breakdown = await self._analytics.breakdown(
            ctx,
            district_id=body.district_id,
            station_id=None,
            from_=from_dt,
            to=to_dt,
            group_by="offense",
        )
        pred = await self._predictions.current(
            ctx, metric=PredictionMetric.risk_score, district_id=body.district_id, top_n=6
        )
        hotspots = await self._predictions.hotspots_current(
            ctx, district_id=body.district_id, limit=5
        )
        advisor = await self._advisor.current_brief(ctx, force=False)

        # XAI for top prediction value if present
        xai: XaiSummaryOut | None = None
        if pred.values:
            try:
                card = await self._explain.decision_card(ctx, pred.values[0].id)
                xai = XaiSummaryOut(
                    scope_name=card.scope_name,
                    summary=card.summary,
                    top_factors=[f.label for f in card.factors[:4]],
                    confidence=card.confidence,
                )
            except Exception:
                xai = None

        delta = overview.kpis.total_incidents_delta_pct
        top_offense = (breakdown.get("items") or [{}])
        top_name = str(top_offense[0].get("name") or "property crime") if top_offense else "property crime"

        hs_labels = [
            str(f.properties.get("label") or f"Hotspot #{f.rank}") for f in hotspots.features[:2]
        ]
        delta_txt = f" ({delta:+.1f}% vs prior window)" if delta is not None else ""
        if body.template_id == "festival":
            exec_summary = (
                f"Festival Security Assessment for {from_d.isoformat()}–{to_d.isoformat()}. "
                f"Observed volume {overview.kpis.total_incidents} incidents{delta_txt}. "
                f"Leading category: {top_name}. "
                f"Forecast focus: {', '.join(hs_labels) if hs_labels else 'commercial / metro fringe'}. "
                "Recommend elevated evening patrol and CCTV emphasis near venues before peak footfall."
            )
        elif body.template_id == "daily":
            exec_summary = (
                f"Daily brief ({to_d.isoformat()}): {overview.kpis.total_incidents} incidents in window, "
                f"{overview.kpis.open_incidents} open, {overview.kpis.high_severity} high/critical. "
                f"{advisor.summary.headline}. "
                f"Immediate watch: {', '.join(hs_labels) if hs_labels else 'no new hotspot labels'}."
            )
        else:
            exec_summary = advisor.summary.body

        insights = [
            InsightOut(title=p.title, body=p.explanation, kind=p.kind)
            for p in advisor.patterns[:4]
        ]
        if body.template_id == "festival":
            insights.insert(
                0,
                InsightOut(
                    title="Event-window risk posture",
                    body=(
                        "Observed + forecast: festival-type windows historically coincide with elevated "
                        f"{top_name} near commercial corridors. Align surge coverage 19:00–22:00."
                    ),
                    kind="forecast",
                ),
            )

        hotspot_rows: list[HotspotOut] = []
        for f in hotspots.features[:5]:
            label = str(f.properties.get("label") or f"Hotspot #{f.rank}")
            score = float(f.score)
            hotspot_rows.append(
                HotspotOut(
                    label=label,
                    risk_level=_risk_band(score),
                    score=score,
                    confidence=0.84,
                    factors=["Incident density", "Recent cluster growth", "Evening concentration"],
                    suggested_action=f"Increase directed patrol passes near {label} during peak hours.",
                )
            )
        for v in pred.values[:3]:
            if len(hotspot_rows) >= 5:
                break
            props = v.properties or {}
            name = str(props.get("station_name") or "Station")
            if any(h.label == name for h in hotspot_rows):
                continue
            hotspot_rows.append(
                HotspotOut(
                    label=name,
                    risk_level=_risk_band(float(v.value)),
                    score=float(v.value),
                    confidence=0.86,
                    factors=[str(props.get("label") or "Elevated residual risk")],
                    suggested_action=f"Review beat plan for {name}; cross-check Decision Card.",
                )
            )

        predictions = [
            PredictionOut(
                scope_name=str((v.properties or {}).get("station_name") or "Station"),
                risk_score=float(v.value),
                risk_band=_risk_band(float(v.value)),
                confidence=0.88 if float(v.value) >= 0.6 else 0.8,
                note=str((v.properties or {}).get("label") or "Model risk score for forecast horizon"),
            )
            for v in pred.values[:5]
        ]

        recommendations = [
            RecommendationOut(
                title=a.title,
                rationale=a.rationale,
                confidence=a.confidence,
                priority=a.priority,
            )
            for a in advisor.actions[:5]
        ]
        if body.template_id == "festival" and not any("festival" in r.title.lower() for r in recommendations):
            recommendations.insert(
                0,
                RecommendationOut(
                    title="Pre-stage surge near venue approaches",
                    rationale="Festival template: elevate visibility before peak footfall; test levers in Simulator.",
                    confidence=0.85,
                    priority="high",
                ),
            )

        resource_plan = [
            ResourcePlanOut(
                division="Central / commercial",
                change="+2 patrol units (evening)",
                note="Aligned to top risk stations and hotspot intensity",
            ),
            ResourcePlanOut(
                division="Eastern fringe",
                change="+1 mobile surveillance team" if hotspots.features else "No change",
                note="Spillover watch if metro / event markers active",
            ),
            ResourcePlanOut(
                division="Citywide reserve",
                change="Hold 1 unit as surge reserve",
                note="Deploy only if volume exceeds prior-window baseline",
            ),
        ]

        checklist = [
            ChecklistItemOut(id="c1", text=recommendations[0].title if recommendations else "Review top hotspot"),
            ChecklistItemOut(id="c2", text="Open Decision Card for highest-risk station"),
            ChecklistItemOut(id="c3", text="Confirm CCTV / parking checks on commercial frontage"),
            ChecklistItemOut(id="c4", text="Run related scenario in Digital Twin if event window applies"),
            ChecklistItemOut(id="c5", text="Brief control room on 19:00–22:00 watch block"),
        ]

        cover = CoverOut(
            title="CrimeLens AI",
            subtitle="AI-Powered Crime Intelligence Report",
            prepared_for="Karnataka State Police",
            classification="Internal Intelligence Brief",
            report_type=tmpl.name,
            date_label=to_d.strftime("%B %Y"),
            range_label=f"{from_d.isoformat()} → {to_d.isoformat()}",
            generated_at=now,
        )

        presenter = [
            PresenterSlideOut(
                section_id="cover",
                title="Cover",
                narration=(
                    f"This is the {tmpl.name} for {cover.range_label}, prepared for Karnataka State Police "
                    "as an internal intelligence brief."
                ),
                drill_href=None,
            ),
            PresenterSlideOut(
                section_id="executive",
                title="Executive Summary",
                narration=exec_summary[:500],
                drill_href="/advisor",
            ),
            PresenterSlideOut(
                section_id="overview",
                title="Crime Overview",
                narration=(
                    f"Observed: {overview.kpis.total_incidents} incidents in the selected window, "
                    f"with {overview.kpis.high_severity} high or critical severity cases."
                ),
                drill_href="/dashboard",
            ),
            PresenterSlideOut(
                section_id="hotspots",
                title="Hotspot Analysis",
                narration=(
                    f"Forecast and detection highlight {len(hotspot_rows)} priority locations, led by "
                    f"{hotspot_rows[0].label}." if hotspot_rows else "No hotspot features in the current run."
                ),
                drill_href="/prediction",
            ),
            PresenterSlideOut(
                section_id="predictions",
                title="Predictions",
                narration=(
                    f"Top forecast risk is {predictions[0].scope_name} at "
                    f"{predictions[0].risk_score * 100:.0f}% score with {predictions[0].confidence * 100:.0f}% confidence."
                    if predictions
                    else "No current prediction values available."
                ),
                drill_href="/explain",
            ),
            PresenterSlideOut(
                section_id="recommendations",
                title="Operational Recommendations",
                narration=(
                    recommendations[0].title + ". " + recommendations[0].rationale
                    if recommendations
                    else "No recommendations generated."
                ),
                drill_href="/simulation",
            ),
            PresenterSlideOut(
                section_id="checklist",
                title="Action Checklist",
                narration="Close with the immediate action checklist so the briefing ends on decisions, not just data.",
                drill_href="/reports",
            ),
        ]

        report = IntelligenceReportData(
            id=str(uuid.uuid4()),
            template_id=tmpl.id,
            cover=cover,
            executive_summary=exec_summary,
            overview=OverviewOut(
                total_incidents=overview.kpis.total_incidents,
                delta_pct=delta,
                open_incidents=overview.kpis.open_incidents,
                high_severity=overview.kpis.high_severity,
                by_severity=[s.model_dump() for s in overview.by_severity],
                by_offense=list(breakdown.get("items") or [])[:8],
                trend_daily=[t.model_dump() for t in overview.trend_daily],
            ),
            insights=insights,
            hotspots=hotspot_rows,
            predictions=predictions,
            xai_summary=xai,
            recommendations=recommendations,
            resource_plan=resource_plan,
            checklist=checklist,
            presenter_script=presenter,
            sources=[
                {"type": "dashboard_overview"},
                {"type": "analytics_breakdown"},
                {"type": "predictions", "run_id": str(pred.run.id) if pred.run else None},
                {"type": "hotspots", "run_id": str(hotspots.run.id) if hotspots.run else None},
                {"type": "advisor_brief", "id": advisor.id},
            ],
            disclaimer=DISCLAIMER,
            generated_at=now,
        )
        _REPORT_CACHE[report.id] = report
        # keep last few
        if len(_REPORT_CACHE) > 20:
            for k in list(_REPORT_CACHE.keys())[:-15]:
                _REPORT_CACHE.pop(k, None)
        return report
