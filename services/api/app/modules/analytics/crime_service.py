"""Crime trends and breakdowns from incidents."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import Select, cast, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Date

from crimelens_domain.identity import AuthContext

from app.infra.db.models import IncidentModel, OffenseTypeModel
from app.modules.analytics.crime_schemas import BreakdownItem, TrendPoint, TrendSeries


class CrimeAnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _scope(
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
        return stmt.where(or_(*clauses))

    async def trends(
        self,
        ctx: AuthContext,
        *,
        district_id: UUID | None,
        station_id: UUID | None,
        from_: datetime | None,
        to: datetime | None,
        interval: str,
    ) -> dict:
        now = datetime.now(UTC)
        window_to = to or now
        window_from = from_ or (window_to - timedelta(days=30))
        day = cast(IncidentModel.occurred_at, Date)
        stmt = select(day, func.count()).select_from(IncidentModel)
        stmt = self._scope(stmt, ctx, district_id, station_id)
        stmt = (
            stmt.where(IncidentModel.occurred_at >= window_from, IncidentModel.occurred_at < window_to)
            .group_by(day)
            .order_by(day)
        )
        rows = (await self._session.execute(stmt)).all()
        points = [TrendPoint(bucket_start=d.isoformat(), count=int(c)) for d, c in rows]
        series = [TrendSeries(key="all", points=points)]
        return {"interval": interval, "series": [s.model_dump() for s in series]}

    async def breakdown(
        self,
        ctx: AuthContext,
        *,
        district_id: UUID | None,
        station_id: UUID | None,
        from_: datetime | None,
        to: datetime | None,
        group_by: str,
    ) -> dict:
        now = datetime.now(UTC)
        window_to = to or now
        window_from = from_ or (window_to - timedelta(days=30))

        if group_by == "severity":
            stmt = select(IncidentModel.severity, func.count()).select_from(IncidentModel)
            stmt = self._scope(stmt, ctx, district_id, station_id)
            stmt = (
                stmt.where(
                    IncidentModel.occurred_at >= window_from,
                    IncidentModel.occurred_at < window_to,
                )
                .group_by(IncidentModel.severity)
                .order_by(func.count().desc())
            )
            rows = (await self._session.execute(stmt)).all()
            items = [
                BreakdownItem(key=sev.value, name=sev.value, count=int(cnt)).model_dump()
                for sev, cnt in rows
            ]
        else:
            stmt = (
                select(OffenseTypeModel.code, OffenseTypeModel.name, func.count())
                .select_from(IncidentModel)
                .join(OffenseTypeModel, OffenseTypeModel.id == IncidentModel.offense_type_id)
            )
            stmt = self._scope(stmt, ctx, district_id, station_id)
            stmt = (
                stmt.where(
                    IncidentModel.occurred_at >= window_from,
                    IncidentModel.occurred_at < window_to,
                )
                .group_by(OffenseTypeModel.code, OffenseTypeModel.name)
                .order_by(func.count().desc())
                .limit(10)
            )
            rows = (await self._session.execute(stmt)).all()
            items = [
                BreakdownItem(key=code, name=name, count=int(cnt)).model_dump()
                for code, name, cnt in rows
            ]
            group_by = "offense"

        return {"group_by": group_by, "items": items}
