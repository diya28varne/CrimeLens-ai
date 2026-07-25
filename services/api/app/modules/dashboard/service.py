"""Dashboard aggregates computed from incidents."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import Select, cast, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Date

from crimelens_domain.identity import AuthContext

from app.infra.db.models import IncidentModel, IncidentStatus, OffenseTypeModel, SeverityLevel
from app.modules.dashboard.schemas import (
    DailyCount,
    DashboardAlert,
    DashboardOverview,
    DashboardScope,
    KpiSet,
    ModelPointer,
    NamedCount,
)


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _scope_filter(
        self,
        stmt: Select,
        ctx: AuthContext,
        district_id: UUID | None,
        station_id: UUID | None,
    ) -> Select:
        stmt = stmt.where(IncidentModel.deleted_at.is_(None))
        if station_id is not None:
            stmt = stmt.where(IncidentModel.station_id == station_id)
        if district_id is not None:
            stmt = stmt.where(IncidentModel.district_id == district_id)
        if ctx.is_superuser:
            return stmt
        clauses = []
        if ctx.allowed_district_ids:
            clauses.append(IncidentModel.district_id.in_(ctx.allowed_district_ids))
        if ctx.allowed_station_ids:
            clauses.append(IncidentModel.station_id.in_(ctx.allowed_station_ids))
        if not clauses:
            return stmt.where(text("false"))
        from sqlalchemy import or_

        return stmt.where(or_(*clauses))

    async def overview(
        self,
        ctx: AuthContext,
        *,
        district_id: UUID | None,
        station_id: UUID | None,
        from_: datetime | None,
        to: datetime | None,
    ) -> DashboardOverview:
        now = datetime.now(UTC)
        window_to = to or now
        window_from = from_ or (window_to - timedelta(days=30))
        prev_to = window_from
        prev_from = window_from - (window_to - window_from)

        total = await self._count(ctx, district_id, station_id, window_from, window_to)
        prev_total = await self._count(ctx, district_id, station_id, prev_from, prev_to)
        delta = None
        if prev_total > 0:
            delta = round(((total - prev_total) / prev_total) * 100.0, 1)
        elif total > 0:
            delta = 100.0

        open_count = await self._count(
            ctx,
            district_id,
            station_id,
            window_from,
            window_to,
            statuses=[
                IncidentStatus.reported,
                IncidentStatus.registered,
                IncidentStatus.under_investigation,
            ],
        )
        high = await self._count(
            ctx,
            district_id,
            station_id,
            window_from,
            window_to,
            severities=[SeverityLevel.high, SeverityLevel.critical],
        )

        by_severity = await self._group_severity(ctx, district_id, station_id, window_from, window_to)
        by_offense = await self._group_offense(ctx, district_id, station_id, window_from, window_to)
        trend = await self._daily_trend(ctx, district_id, station_id, window_from, window_to)

        return DashboardOverview(
            scope=DashboardScope.model_validate(
                {
                    "district_id": district_id,
                    "station_id": station_id,
                    "from": window_from,
                    "to": window_to,
                }
            ),
            kpis=KpiSet(
                total_incidents=total,
                total_incidents_delta_pct=delta,
                open_incidents=open_count,
                high_severity=high,
                hotspot_count=0,
                avg_risk_score=None,
            ),
            by_severity=by_severity,
            by_offense_top=by_offense,
            trend_daily=trend,
            model=ModelPointer(is_stale=True),
        )

    async def alerts(
        self,
        ctx: AuthContext,
        *,
        district_id: UUID | None,
        station_id: UUID | None,
    ) -> list[DashboardAlert]:
        overview = await self.overview(
            ctx, district_id=district_id, station_id=station_id, from_=None, to=None
        )
        alerts: list[DashboardAlert] = []
        delta = overview.kpis.total_incidents_delta_pct
        if delta is not None and delta >= 25:
            alerts.append(
                DashboardAlert(
                    id="volume-spike",
                    severity="warning",
                    title="Incident volume elevated",
                    body=f"Total incidents are up {delta}% vs prior window.",
                    district_id=district_id,
                    station_id=station_id,
                    metric="total_incidents_delta_pct",
                    value=delta,
                    baseline=0,
                    href="/analytics",
                )
            )
        if overview.kpis.high_severity >= max(3, overview.kpis.total_incidents * 0.35):
            alerts.append(
                DashboardAlert(
                    id="high-severity-share",
                    severity="critical",
                    title="High-severity concentration",
                    body=f"{overview.kpis.high_severity} high/critical incidents in the current window.",
                    district_id=district_id,
                    station_id=station_id,
                    metric="high_severity",
                    value=float(overview.kpis.high_severity),
                    href="/map",
                )
            )
        if not alerts:
            alerts.append(
                DashboardAlert(
                    id="stable",
                    severity="info",
                    title="No critical anomalies",
                    body="Current window looks stable relative to simple baselines.",
                    district_id=district_id,
                    station_id=station_id,
                    metric="status",
                    value=0,
                )
            )
        return alerts

    async def _count(
        self,
        ctx: AuthContext,
        district_id: UUID | None,
        station_id: UUID | None,
        from_: datetime,
        to: datetime,
        *,
        statuses: list[IncidentStatus] | None = None,
        severities: list[SeverityLevel] | None = None,
    ) -> int:
        stmt = select(func.count()).select_from(IncidentModel)
        stmt = self._scope_filter(stmt, ctx, district_id, station_id)
        stmt = stmt.where(IncidentModel.occurred_at >= from_, IncidentModel.occurred_at < to)
        if statuses:
            stmt = stmt.where(IncidentModel.status.in_(statuses))
        if severities:
            stmt = stmt.where(IncidentModel.severity.in_(severities))
        return int(await self._session.scalar(stmt) or 0)

    async def _group_severity(
        self,
        ctx: AuthContext,
        district_id: UUID | None,
        station_id: UUID | None,
        from_: datetime,
        to: datetime,
    ) -> list[NamedCount]:
        stmt = select(IncidentModel.severity, func.count()).select_from(IncidentModel)
        stmt = self._scope_filter(stmt, ctx, district_id, station_id)
        stmt = (
            stmt.where(IncidentModel.occurred_at >= from_, IncidentModel.occurred_at < to)
            .group_by(IncidentModel.severity)
            .order_by(func.count().desc())
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            NamedCount(key=sev.value, name=sev.value, count=int(cnt)) for sev, cnt in rows
        ]

    async def _group_offense(
        self,
        ctx: AuthContext,
        district_id: UUID | None,
        station_id: UUID | None,
        from_: datetime,
        to: datetime,
        limit: int = 5,
    ) -> list[NamedCount]:
        stmt = (
            select(OffenseTypeModel.id, OffenseTypeModel.name, OffenseTypeModel.code, func.count())
            .select_from(IncidentModel)
            .join(OffenseTypeModel, OffenseTypeModel.id == IncidentModel.offense_type_id)
        )
        stmt = self._scope_filter(stmt, ctx, district_id, station_id)
        stmt = (
            stmt.where(IncidentModel.occurred_at >= from_, IncidentModel.occurred_at < to)
            .group_by(OffenseTypeModel.id, OffenseTypeModel.name, OffenseTypeModel.code)
            .order_by(func.count().desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).all()
        return [
            NamedCount(key=str(oid), name=name or code, count=int(cnt))
            for oid, name, code, cnt in rows
        ]

    async def _daily_trend(
        self,
        ctx: AuthContext,
        district_id: UUID | None,
        station_id: UUID | None,
        from_: datetime,
        to: datetime,
    ) -> list[DailyCount]:
        day = cast(IncidentModel.occurred_at, Date)
        stmt = select(day, func.count()).select_from(IncidentModel)
        stmt = self._scope_filter(stmt, ctx, district_id, station_id)
        stmt = (
            stmt.where(IncidentModel.occurred_at >= from_, IncidentModel.occurred_at < to)
            .group_by(day)
            .order_by(day)
        )
        rows = (await self._session.execute(stmt)).all()
        return [DailyCount(date=d.isoformat(), count=int(c)) for d, c in rows]
