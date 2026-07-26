"""Crime trends and breakdowns from incidents."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from math import sqrt
from uuid import UUID

from sqlalchemy import Select, cast, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.types import Date

from crimelens_domain.identity import AuthContext

from app.infra.db.models import IncidentModel, OffenseTypeModel
from app.modules.analytics.crime_schemas import BreakdownItem, TrendPoint, TrendSeries

_DOW_LABELS = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")


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

    async def _count_window(
        self,
        ctx: AuthContext,
        *,
        district_id: UUID | None,
        station_id: UUID | None,
        window_from: datetime,
        window_to: datetime,
    ) -> int:
        stmt = select(func.count()).select_from(IncidentModel)
        stmt = self._scope(stmt, ctx, district_id, station_id)
        stmt = stmt.where(
            IncidentModel.occurred_at >= window_from,
            IncidentModel.occurred_at < window_to,
        )
        return int((await self._session.execute(stmt)).scalar_one())

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

    async def insights(
        self,
        ctx: AuthContext,
        *,
        district_id: UUID | None,
        station_id: UUID | None,
        days: int = 30,
    ) -> dict:
        """Analyst-grade summary: period compare, temporal patterns, concentration, spikes."""
        now = datetime.now(UTC)
        days = max(7, min(days, 90))
        window_to = now
        window_from = window_to - timedelta(days=days)
        prior_to = window_from
        prior_from = prior_to - timedelta(days=days)

        current_total = await self._count_window(
            ctx,
            district_id=district_id,
            station_id=station_id,
            window_from=window_from,
            window_to=window_to,
        )
        prior_total = await self._count_window(
            ctx,
            district_id=district_id,
            station_id=station_id,
            window_from=prior_from,
            window_to=prior_to,
        )
        delta = current_total - prior_total
        pct_change = (
            round((delta / prior_total) * 100, 1) if prior_total > 0 else (100.0 if current_total else 0.0)
        )

        day = cast(IncidentModel.occurred_at, Date)
        daily_stmt = select(day, func.count()).select_from(IncidentModel)
        daily_stmt = self._scope(daily_stmt, ctx, district_id, station_id)
        daily_stmt = (
            daily_stmt.where(
                IncidentModel.occurred_at >= window_from,
                IncidentModel.occurred_at < window_to,
            )
            .group_by(day)
            .order_by(day)
        )
        daily_rows = (await self._session.execute(daily_stmt)).all()
        daily_counts = [int(c) for _, c in daily_rows]
        daily_series = [
            {"date": d.isoformat(), "count": int(c)} for d, c in daily_rows
        ]

        mean = sum(daily_counts) / len(daily_counts) if daily_counts else 0.0
        variance = (
            sum((x - mean) ** 2 for x in daily_counts) / len(daily_counts) if daily_counts else 0.0
        )
        std = sqrt(variance)
        threshold = mean + (1.5 * std) if std > 0 else (mean * 1.5 if mean > 0 else 0)
        spikes = [
            {"date": d.isoformat(), "count": int(c), "vs_mean": round(int(c) - mean, 1)}
            for d, c in daily_rows
            if int(c) >= threshold and int(c) > 0
        ]
        spikes.sort(key=lambda s: s["count"], reverse=True)
        spikes = spikes[:5]

        hour_expr = func.extract("hour", IncidentModel.occurred_at)
        hour_stmt = select(hour_expr, func.count()).select_from(IncidentModel)
        hour_stmt = self._scope(hour_stmt, ctx, district_id, station_id)
        hour_stmt = (
            hour_stmt.where(
                IncidentModel.occurred_at >= window_from,
                IncidentModel.occurred_at < window_to,
            )
            .group_by(hour_expr)
            .order_by(hour_expr)
        )
        hour_map = {int(h): int(c) for h, c in (await self._session.execute(hour_stmt)).all()}
        by_hour = [{"hour": h, "count": hour_map.get(h, 0)} for h in range(24)]
        peak_hour = max(by_hour, key=lambda x: x["count"]) if current_total else {"hour": 0, "count": 0}

        dow_expr = func.extract("dow", IncidentModel.occurred_at)
        dow_stmt = select(dow_expr, func.count()).select_from(IncidentModel)
        dow_stmt = self._scope(dow_stmt, ctx, district_id, station_id)
        dow_stmt = (
            dow_stmt.where(
                IncidentModel.occurred_at >= window_from,
                IncidentModel.occurred_at < window_to,
            )
            .group_by(dow_expr)
            .order_by(dow_expr)
        )
        dow_map = {int(d): int(c) for d, c in (await self._session.execute(dow_stmt)).all()}
        by_dow = [
            {"dow": i, "label": _DOW_LABELS[i], "count": dow_map.get(i, 0)} for i in range(7)
        ]
        weekend = dow_map.get(0, 0) + dow_map.get(6, 0)
        weekday = current_total - weekend
        weekend_days = max(1, round(days * 2 / 7))
        weekday_days = max(1, days - weekend_days)
        weekend_per_day = round(weekend / weekend_days, 1)
        weekday_per_day = round(weekday / weekday_days, 1)

        offense_stmt = (
            select(OffenseTypeModel.code, OffenseTypeModel.name, func.count())
            .select_from(IncidentModel)
            .join(OffenseTypeModel, OffenseTypeModel.id == IncidentModel.offense_type_id)
        )
        offense_stmt = self._scope(offense_stmt, ctx, district_id, station_id)
        offense_stmt = (
            offense_stmt.where(
                IncidentModel.occurred_at >= window_from,
                IncidentModel.occurred_at < window_to,
            )
            .group_by(OffenseTypeModel.code, OffenseTypeModel.name)
            .order_by(func.count().desc())
        )
        offense_rows = (await self._session.execute(offense_stmt)).all()
        offense_counts = [int(c) for _, _, c in offense_rows]
        top3 = sum(offense_counts[:3]) if offense_counts else 0
        top1_share = round((offense_counts[0] / current_total) * 100, 1) if current_total and offense_counts else 0.0
        top3_share = round((top3 / current_total) * 100, 1) if current_total else 0.0
        # Herfindahl–Hirschman Index on offense shares (0–1 scale)
        hhi = (
            round(sum((c / current_total) ** 2 for c in offense_counts), 3)
            if current_total and offense_counts
            else 0.0
        )
        concentration = "high" if hhi >= 0.25 else ("moderate" if hhi >= 0.12 else "dispersed")

        sev_stmt = select(IncidentModel.severity, func.count()).select_from(IncidentModel)
        sev_stmt = self._scope(sev_stmt, ctx, district_id, station_id)
        sev_stmt = sev_stmt.where(
            IncidentModel.occurred_at >= window_from,
            IncidentModel.occurred_at < window_to,
        ).group_by(IncidentModel.severity)
        sev_map = {sev.value: int(c) for sev, c in (await self._session.execute(sev_stmt)).all()}
        high_crit = sev_map.get("high", 0) + sev_map.get("critical", 0)
        high_crit_share = round((high_crit / current_total) * 100, 1) if current_total else 0.0

        findings: list[dict] = []
        if prior_total > 0:
            direction = "up" if delta > 0 else ("down" if delta < 0 else "flat")
            findings.append(
                {
                    "id": "period_change",
                    "severity": "high" if abs(pct_change) >= 20 else ("medium" if abs(pct_change) >= 8 else "low"),
                    "title": f"Volume {direction} {abs(pct_change):.0f}% vs prior {days}d",
                    "detail": (
                        f"{current_total} incidents this window vs {prior_total} prior "
                        f"({delta:+d}). Dashboard shows the latest slice; this is period-over-period impact."
                    ),
                }
            )
        if spikes:
            top_spike = spikes[0]
            findings.append(
                {
                    "id": "spike",
                    "severity": "high",
                    "title": f"Spike day: {top_spike['date']} ({top_spike['count']} incidents)",
                    "detail": (
                        f"{len(spikes)} day(s) exceeded mean+1.5σ (mean {mean:.1f}/day). "
                        "Investigate those dates in Story or Hotspots."
                    ),
                }
            )
        if current_total and peak_hour["count"] > 0:
            findings.append(
                {
                    "id": "peak_hour",
                    "severity": "medium",
                    "title": f"Peak hour {peak_hour['hour']:02d}:00 ({peak_hour['count']} incidents)",
                    "detail": "Concentrate patrol / CCTV attention around this hour band.",
                }
            )
        if weekend_per_day > weekday_per_day * 1.15:
            findings.append(
                {
                    "id": "weekend",
                    "severity": "medium",
                    "title": "Weekend intensity higher than weekdays",
                    "detail": (
                        f"~{weekend_per_day}/day on weekends vs ~{weekday_per_day}/day on weekdays."
                    ),
                }
            )
        elif weekday_per_day > weekend_per_day * 1.15:
            findings.append(
                {
                    "id": "weekday",
                    "severity": "medium",
                    "title": "Weekday intensity dominates",
                    "detail": (
                        f"~{weekday_per_day}/day on weekdays vs ~{weekend_per_day}/day on weekends."
                    ),
                }
            )
        if offense_rows and top1_share >= 25:
            code, name, cnt = offense_rows[0]
            findings.append(
                {
                    "id": "offense_concentration",
                    "severity": "high" if top1_share >= 40 else "medium",
                    "title": f"{name} is {top1_share}% of volume",
                    "detail": (
                        f"Top-3 offenses = {top3_share}% (HHI {hhi}, {concentration}). "
                        "Use Advisor for resource tilt toward this pattern."
                    ),
                }
            )
        if high_crit_share >= 20:
            findings.append(
                {
                    "id": "severity_mix",
                    "severity": "high",
                    "title": f"High/critical share at {high_crit_share}%",
                    "detail": "Severity mix is elevated — not just volume. Prioritize response capacity.",
                }
            )
        if not findings and current_total:
            findings.append(
                {
                    "id": "stable",
                    "severity": "low",
                    "title": "No sharp anomalies in this window",
                    "detail": "Volume and mix look relatively stable. Dig into socio-economic correlations below.",
                }
            )

        return {
            "window_days": days,
            "current": {
                "from": window_from.isoformat(),
                "to": window_to.isoformat(),
                "total": current_total,
            },
            "prior": {
                "from": prior_from.isoformat(),
                "to": prior_to.isoformat(),
                "total": prior_total,
            },
            "delta": delta,
            "pct_change": pct_change,
            "daily": daily_series,
            "spikes": spikes,
            "by_hour": by_hour,
            "by_dow": by_dow,
            "weekend": {
                "count": weekend,
                "per_day": weekend_per_day,
            },
            "weekday": {
                "count": weekday,
                "per_day": weekday_per_day,
            },
            "peak_hour": peak_hour,
            "concentration": {
                "top1_share_pct": top1_share,
                "top3_share_pct": top3_share,
                "hhi": hhi,
                "label": concentration,
                "top_offense": (
                    {"code": offense_rows[0][0], "name": offense_rows[0][1], "count": int(offense_rows[0][2])}
                    if offense_rows
                    else None
                ),
            },
            "severity": {
                "high_critical_count": high_crit,
                "high_critical_share_pct": high_crit_share,
                "by_severity": sev_map,
            },
            "findings": findings,
        }
