"""Crime Story Playback — temporal frames, chapters, detective mode."""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from geoalchemy2 import Geometry
from sqlalchemy import Select, cast, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from crimelens_domain.identity import AuthContext
from crimelens_domain.shared.errors import NotFoundError

from app.infra.db.models import IncidentModel, OffenseTypeModel
from app.modules.story.events import story_events_for_range
from app.modules.story.schemas import (
    DensityCell,
    DetectiveBriefData,
    DetectiveFinding,
    DetectiveRequest,
    JourneyData,
    JourneyStep,
    StoryChapter,
    StoryEvent,
    StoryFrame,
    StoryFramesData,
    StoryPoint,
    StoryRangeData,
)

DISCLAIMER = (
    "Story Playback is grounded in seeded / recorded incidents. "
    "Narratives are Observed transitions — coincidence is not proof of causation."
)

GRID = 0.008  # ~0.9km cells for demo density


class StoryService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _scope(self, stmt: Select, ctx: AuthContext, district_id: UUID | None) -> Select:
        stmt = stmt.where(IncidentModel.deleted_at.is_(None))
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

    async def _load_incidents(
        self,
        ctx: AuthContext,
        *,
        from_: datetime,
        to: datetime,
        offense_code: str | None,
        district_id: UUID | None,
    ) -> list[dict[str, Any]]:
        loc_geom = cast(IncidentModel.location, Geometry)
        stmt = (
            select(
                IncidentModel.id,
                IncidentModel.occurred_at,
                IncidentModel.severity,
                IncidentModel.title,
                IncidentModel.status,
                IncidentModel.created_at,
                OffenseTypeModel.code,
                OffenseTypeModel.name,
                func.ST_X(loc_geom),
                func.ST_Y(loc_geom),
            )
            .join(OffenseTypeModel, OffenseTypeModel.id == IncidentModel.offense_type_id)
            .where(
                IncidentModel.occurred_at >= from_,
                IncidentModel.occurred_at < to,
            )
        )
        stmt = self._scope(stmt, ctx, district_id)
        if offense_code:
            stmt = stmt.where(OffenseTypeModel.code == offense_code)
        stmt = stmt.order_by(IncidentModel.occurred_at.asc())
        rows = (await self._session.execute(stmt)).all()
        out: list[dict[str, Any]] = []
        for r in rows:
            lon, lat = r[8], r[9]
            if lon is None or lat is None:
                continue
            out.append(
                {
                    "id": str(r[0]),
                    "occurred_at": r[1],
                    "severity": r[2].value if hasattr(r[2], "value") else str(r[2]),
                    "title": r[3],
                    "status": r[4].value if hasattr(r[4], "value") else str(r[4]),
                    "created_at": r[5],
                    "offense_code": r[6],
                    "offense_name": r[7],
                    "lon": float(lon),
                    "lat": float(lat),
                }
            )
        return out

    async def resolve_range(
        self,
        ctx: AuthContext,
        *,
        from_: date | None,
        to: date | None,
        offense_code: str | None,
        district_id: UUID | None,
    ) -> StoryRangeData:
        now = datetime.now(UTC)
        end = datetime.combine(to or now.date(), datetime.max.time(), tzinfo=UTC)
        start_date = from_ or (now.date() - timedelta(days=90))
        start = datetime.combine(start_date, datetime.min.time(), tzinfo=UTC)
        incidents = await self._load_incidents(
            ctx, from_=start, to=end, offense_code=offense_code, district_id=district_id
        )
        codes = sorted({i["offense_code"] for i in incidents})
        return StoryRangeData.model_validate(
            {
                "from": start.date(),
                "to": end.date(),
                "total_incidents": len(incidents),
                "offense_codes": codes,
                "bucket": "day",
            }
        )

    def _cell_key(self, lon: float, lat: float) -> tuple[float, float]:
        return (math.floor(lon / GRID) * GRID, math.floor(lat / GRID) * GRID)

    def _density(
        self, points: list[dict[str, Any]], prev_counts: dict[tuple[float, float], int]
    ) -> list[DensityCell]:
        counts: dict[tuple[float, float], int] = defaultdict(int)
        for p in points:
            counts[self._cell_key(p["lon"], p["lat"])] += 1
        max_c = max(counts.values()) if counts else 1
        cells: list[DensityCell] = []
        for (lon, lat), count in counts.items():
            intensity = count / max_c
            prev = prev_counts.get((lon, lat), 0)
            if count >= 5:
                stage = "critical"
            elif count >= 4:
                stage = "emerging_hotspot"
            elif count >= 3:
                stage = "growing"
            elif count >= 2:
                stage = "small_cluster"
            else:
                stage = "individual"
            if prev >= 3 and count < prev:
                stage = "easing"
            cells.append(
                DensityCell(
                    lon=lon + GRID / 2,
                    lat=lat + GRID / 2,
                    count=count,
                    intensity=round(intensity, 3),
                    stage=stage,  # type: ignore[arg-type]
                )
            )
        cells.sort(key=lambda c: c.count, reverse=True)
        return cells[:40]

    async def frames(
        self,
        ctx: AuthContext,
        *,
        from_: date | None,
        to: date | None,
        offense_code: str | None,
        district_id: UUID | None,
    ) -> StoryFramesData:
        range_meta = await self.resolve_range(
            ctx, from_=from_, to=to, offense_code=offense_code, district_id=district_id
        )
        start = datetime.combine(range_meta.from_, datetime.min.time(), tzinfo=UTC)
        end = datetime.combine(range_meta.to, datetime.max.time(), tzinfo=UTC) + timedelta(days=1)
        incidents = await self._load_incidents(
            ctx, from_=start, to=end, offense_code=offense_code, district_id=district_id
        )

        by_day: dict[date, list[dict[str, Any]]] = defaultdict(list)
        for inc in incidents:
            by_day[inc["occurred_at"].date()].append(inc)

        # Walk every day in range so playback is smooth even on quiet days
        frames: list[StoryFrame] = []
        cumulative: list[dict[str, Any]] = []
        prev_counts: dict[tuple[float, float], int] = {}
        cursor = range_meta.from_
        while cursor <= range_meta.to:
            new_pts = by_day.get(cursor, [])
            cumulative.extend(new_pts)
            density = self._density(cumulative, prev_counts)
            prev_counts = defaultdict(int)
            for p in cumulative:
                prev_counts[self._cell_key(p["lon"], p["lat"])] += 1

            # Keep payload light: only emit points up to current day (already cumulative)
            # Cap density cells; points needed for map — OK for demo size
            frames.append(
                StoryFrame(
                    t=cursor,
                    cumulative_count=len(cumulative),
                    new_count=len(new_pts),
                    new_points=[
                        StoryPoint(
                            id=p["id"],
                            lon=p["lon"],
                            lat=p["lat"],
                            offense_code=p["offense_code"],
                            offense_name=p["offense_name"],
                            severity=p["severity"],
                            occurred_at=p["occurred_at"],
                            title=p["title"],
                        )
                        for p in new_pts
                    ],
                    density_cells=density,
                )
            )
            cursor += timedelta(days=1)

        return StoryFramesData(range=range_meta, frames=frames)

    async def chapters(
        self,
        ctx: AuthContext,
        *,
        from_: date | None,
        to: date | None,
        offense_code: str | None,
        district_id: UUID | None,
    ) -> list[StoryChapter]:
        data = await self.frames(
            ctx, from_=from_, to=to, offense_code=offense_code, district_id=district_id
        )
        frames = data.frames
        if len(frames) < 8:
            return []

        chapters: list[StoryChapter] = []
        # Rolling 7-day new counts
        for i in range(7, len(frames)):
            window = frames[i - 6 : i + 1]
            prior = frames[max(0, i - 13) : i - 6] or frames[: i - 6]
            w_new = sum(f.new_count for f in window)
            p_new = sum(f.new_count for f in prior) if prior else 0
            if p_new == 0 and w_new >= 3:
                pct = 100.0
            elif p_new == 0:
                continue
            else:
                pct = ((w_new - p_new) / p_new) * 100.0
            if pct >= 40 and w_new >= 3:
                top_cell = max(
                    (c for f in window for c in f.density_cells),
                    key=lambda c: c.count,
                    default=None,
                )
                where = (
                    f"near {top_cell.lon:.3f}, {top_cell.lat:.3f} ({top_cell.stage})"
                    if top_cell
                    else "across the watched jurisdiction"
                )
                chapters.append(
                    StoryChapter(
                        id=f"ch-spike-{frames[i].t.isoformat()}",
                        t_start=window[0].t,
                        t_end=window[-1].t,
                        title=f"Activity surge +{pct:.0f}%",
                        narrative=(
                            f"Observed: between {window[0].t.isoformat()} and {window[-1].t.isoformat()}, "
                            f"new incidents rose to {w_new} versus {p_new} in the prior week "
                            f"({pct:+.0f}%). Concentration {where}. "
                            "Treat as a temporal transition — verify with local knowledge."
                        ),
                        metrics={"window_new": w_new, "prior_new": p_new, "pct": round(pct, 1)},
                        sources=[{"type": "story_frames", "t_end": frames[i].t.isoformat()}],
                    )
                )

        # Hotspot birth: first day a cell hits emerging_hotspot
        seen_hot: set[tuple[float, float]] = set()
        for f in frames:
            for c in f.density_cells:
                key = (round(c.lon, 4), round(c.lat, 4))
                if c.stage in {"emerging_hotspot", "critical"} and key not in seen_hot:
                    seen_hot.add(key)
                    chapters.append(
                        StoryChapter(
                            id=f"ch-hot-{f.t.isoformat()}-{key[0]}",
                            t_start=f.t,
                            t_end=f.t,
                            title="Hotspot stage reached",
                            narrative=(
                                f"Observed: a density cell crossed into '{c.stage}' on {f.t.isoformat()} "
                                f"with {c.count} cumulative incidents in-cell. "
                                "This is the 'birth/growth' moment of a hotspot story, not a guarantee of future crime."
                            ),
                            metrics={"count": c.count, "stage": c.stage, "lon": c.lon, "lat": c.lat},
                            sources=[{"type": "density_cell", "t": f.t.isoformat()}],
                        )
                    )

        # Easing chapter
        for f in frames:
            easing = [c for c in f.density_cells if c.stage == "easing"]
            if easing:
                chapters.append(
                    StoryChapter(
                        id=f"ch-ease-{f.t.isoformat()}",
                        t_start=f.t,
                        t_end=f.t,
                        title="Cluster intensity easing",
                        narrative=(
                            f"Observed: on {f.t.isoformat()}, {len(easing)} previously active cell(s) show "
                            "easing intensity versus earlier cumulative peaks. "
                            "If an intervention marker is nearby on the timeline, treat linkage as hypothesis only."
                        ),
                        metrics={"easing_cells": len(easing)},
                        sources=[{"type": "density_cell", "t": f.t.isoformat()}],
                    )
                )
                break

        # Deduplicate / cap
        uniq: dict[str, StoryChapter] = {}
        for ch in sorted(chapters, key=lambda c: c.t_start):
            uniq[ch.id] = ch
        return list(uniq.values())[:8]

    def events(self, *, from_: date | None, to: date | None) -> list[StoryEvent]:
        now = datetime.now(UTC).date()
        start = from_ or (now - timedelta(days=90))
        end = to or now
        return story_events_for_range(start, end)

    async def detective(self, ctx: AuthContext, body: DetectiveRequest) -> DetectiveBriefData:
        half = body.window_days
        window_to = body.cursor_at
        window_from = body.cursor_at - timedelta(days=half - 1)
        prior_to = window_from - timedelta(days=1)
        prior_from = prior_to - timedelta(days=half - 1)

        start = datetime.combine(window_from, datetime.min.time(), tzinfo=UTC)
        end = datetime.combine(window_to + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
        cur = await self._load_incidents(
            ctx,
            from_=start,
            to=end,
            offense_code=body.offense_code,
            district_id=body.district_id,
        )
        p_start = datetime.combine(prior_from, datetime.min.time(), tzinfo=UTC)
        p_end = datetime.combine(prior_to + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
        prior = await self._load_incidents(
            ctx,
            from_=p_start,
            to=p_end,
            offense_code=body.offense_code,
            district_id=body.district_id,
        )

        cur_n, prior_n = len(cur), len(prior)
        if prior_n == 0:
            pct = 100.0 if cur_n else 0.0
        else:
            pct = ((cur_n - prior_n) / prior_n) * 100.0

        by_off: dict[str, int] = defaultdict(int)
        for i in cur:
            by_off[i["offense_code"]] += 1
        top_off = max(by_off.items(), key=lambda kv: kv[1]) if by_off else ("n/a", 0)

        density = self._density(cur, {})
        top_cell = density[0] if density else None
        spill = density[1] if len(density) > 1 else None

        events = [e for e in self.events(from_=window_from, to=window_to)]

        findings = [
            DetectiveFinding(
                question="Why did activity change in this window?",
                answer=(
                    f"Observed: {cur_n} incidents from {window_from} to {window_to} versus {prior_n} "
                    f"in the prior {half}-day window ({pct:+.0f}%). "
                    f"Leading offense code: {top_off[0]} ({top_off[1]})."
                ),
                evidence=[
                    f"current_count={cur_n}",
                    f"prior_count={prior_n}",
                    f"top_offense={top_off[0]}:{top_off[1]}",
                ],
            ),
            DetectiveFinding(
                question="Where was spatial focus?",
                answer=(
                    f"Observed: strongest density cell stage '{top_cell.stage}' with {top_cell.count} points "
                    f"near {top_cell.lon:.4f}, {top_cell.lat:.4f}."
                    if top_cell
                    else "Observed: insufficient points to form a density focus in this window."
                ),
                evidence=[f"cells={len(density)}"],
            ),
            DetectiveFinding(
                question="Did nearby areas rise next?",
                answer=(
                    f"Observed: secondary cell with {spill.count} incidents near "
                    f"{spill.lon:.4f}, {spill.lat:.4f} — possible spillover candidate."
                    if spill
                    else "Observed: no clear secondary cluster in-window."
                ),
                evidence=["compare density ranks 1–2"],
            ),
            DetectiveFinding(
                question="Any timeline events in this window?",
                answer=(
                    "Observed markers: " + "; ".join(f"{e.label} ({e.t})" for e in events)
                    if events
                    else "Observed: no seeded event markers inside this window."
                ),
                evidence=[e.id for e in events],
            ),
        ]

        actions = [
            "Hold the map on this cursor date and review cumulative density stage.",
            "Filter Pattern Replay to the leading offense code and re-play the week.",
        ]
        preset = None
        if events and any(e.kind == "festival" for e in events):
            actions.append("Test Weekend Festival levers in the Digital Twin Simulator.")
            preset = "weekend_festival"
        elif pct > 20:
            actions.append("Compare evening coverage options in Simulation (VIP / patrol uplift).")
            preset = "vip_movement"

        conf = 0.9 if cur_n >= 5 else 0.78 if cur_n >= 2 else 0.7
        direction = "increased" if pct > 5 else "decreased" if pct < -5 else "held steady"
        return DetectiveBriefData(
            cursor_at=body.cursor_at,
            window_from=window_from,
            window_to=window_to,
            headline=f"Window activity {direction} ({pct:+.0f}% vs prior {half}d)",
            findings=findings,
            suggested_actions=actions,
            simulation_preset_id=preset,
            disclaimer=DISCLAIMER,
            confidence=conf,
        )

    async def journey(self, ctx: AuthContext, incident_id: UUID) -> JourneyData:
        stmt = (
            select(IncidentModel, OffenseTypeModel)
            .join(OffenseTypeModel, OffenseTypeModel.id == IncidentModel.offense_type_id)
            .where(IncidentModel.id == incident_id, IncidentModel.deleted_at.is_(None))
        )
        stmt = self._scope(stmt, ctx, None)
        row = (await self._session.execute(stmt)).first()
        if not row:
            raise NotFoundError("Incident not found", details={"code": "NOT_FOUND"})
        inc, offense = row
        # Nearby similar in ±14 days, same offense
        from_ = inc.occurred_at - timedelta(days=14)
        to = inc.occurred_at + timedelta(days=14)
        nearby = await self._load_incidents(
            ctx, from_=from_, to=to, offense_code=offense.code, district_id=inc.district_id
        )
        nearby_n = max(0, len(nearby) - 1)

        steps = [
            JourneyStep(
                key="reported",
                label="Reported",
                at=inc.occurred_at,
                detail=inc.title or offense.name,
            ),
            JourneyStep(
                key="registered",
                label=f"Status: {inc.status.value}",
                at=inc.created_at,
                detail="Case status from incident store",
            ),
            JourneyStep(
                key="similar",
                label="Similar incidents nearby",
                at=None,
                detail=f"{nearby_n} other {offense.code} events within ±14 days in district",
            ),
            JourneyStep(
                key="pattern",
                label="Pattern context",
                at=None,
                detail="Open Story Playback filtered to this offense to see cluster formation",
            ),
            JourneyStep(
                key="closed",
                label="Investigation state",
                at=None,
                detail="Lifecycle continues with case management — demo ends at current status",
            ),
        ]
        return JourneyData(
            incident_id=inc.id,
            title=inc.title or offense.name,
            offense_code=offense.code,
            steps=steps,
            nearby_similar=nearby_n,
            disclaimer=DISCLAIMER,
        )
