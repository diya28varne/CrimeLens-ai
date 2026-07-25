"""Incident persistence and spatial queries."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from geoalchemy2 import Geometry
from sqlalchemy import Select, cast, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.models import (
    IncidentModel,
    IncidentStatus,
    IngestBatchModel,
    OffenseCategoryModel,
    OffenseTypeModel,
    PoliceStationModel,
    SeverityLevel,
)


class IncidentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _lon_lat_cols():
        geom = cast(IncidentModel.location, Geometry)
        return func.ST_X(geom).label("lon"), func.ST_Y(geom).label("lat")

    def _base_stmt(self) -> Select:
        lon, lat = self._lon_lat_cols()
        return (
            select(IncidentModel, OffenseTypeModel, lon, lat)
            .join(OffenseTypeModel, OffenseTypeModel.id == IncidentModel.offense_type_id)
            .where(IncidentModel.deleted_at.is_(None))
        )

    def _apply_auth_scope(
        self,
        stmt: Select,
        *,
        district_ids: list[UUID] | None,
        station_ids: list[UUID] | None,
    ) -> Select:
        if district_ids is None:
            return stmt
        if not district_ids and not station_ids:
            return stmt.where(text("false"))
        clauses = []
        if district_ids:
            clauses.append(IncidentModel.district_id.in_(district_ids))
        if station_ids:
            clauses.append(IncidentModel.station_id.in_(station_ids))
        return stmt.where(or_(*clauses))

    async def list_incidents(
        self,
        *,
        district_ids: list[UUID] | None,
        station_ids: list[UUID] | None,
        district_id: UUID | None,
        station_id: UUID | None,
        offense_type_id: UUID | None,
        status: str | None,
        severity: str | None,
        occurred_from: datetime | None,
        occurred_to: datetime | None,
        q: str | None,
        limit: int,
        cursor_occurred_at: datetime | None,
        cursor_id: UUID | None,
    ) -> list[tuple[IncidentModel, OffenseTypeModel, float, float]]:
        stmt = self._apply_auth_scope(
            self._base_stmt(),
            district_ids=district_ids,
            station_ids=station_ids,
        )
        if district_id is not None:
            stmt = stmt.where(IncidentModel.district_id == district_id)
        if station_id is not None:
            stmt = stmt.where(IncidentModel.station_id == station_id)
        if offense_type_id is not None:
            stmt = stmt.where(IncidentModel.offense_type_id == offense_type_id)
        if status is not None:
            stmt = stmt.where(IncidentModel.status == IncidentStatus(status))
        if severity is not None:
            stmt = stmt.where(IncidentModel.severity == SeverityLevel(severity))
        if occurred_from is not None:
            stmt = stmt.where(IncidentModel.occurred_at >= occurred_from)
        if occurred_to is not None:
            stmt = stmt.where(IncidentModel.occurred_at < occurred_to)
        if q:
            like = f"%{q}%"
            stmt = stmt.where(
                or_(IncidentModel.external_ref.ilike(like), IncidentModel.title.ilike(like))
            )
        if cursor_occurred_at is not None and cursor_id is not None:
            stmt = stmt.where(
                or_(
                    IncidentModel.occurred_at < cursor_occurred_at,
                    (IncidentModel.occurred_at == cursor_occurred_at)
                    & (IncidentModel.id < cursor_id),
                )
            )
        stmt = stmt.order_by(IncidentModel.occurred_at.desc(), IncidentModel.id.desc()).limit(limit)
        rows = await self._session.execute(stmt)
        return [(r[0], r[1], float(r[2]), float(r[3])) for r in rows.all()]

    async def get_incident(
        self, incident_id: UUID
    ) -> tuple[IncidentModel, OffenseTypeModel, float, float] | None:
        stmt = self._base_stmt().where(IncidentModel.id == incident_id)
        row = (await self._session.execute(stmt)).first()
        if row is None:
            return None
        return row[0], row[1], float(row[2]), float(row[3])

    async def list_offense_types(self) -> list[tuple[OffenseTypeModel, OffenseCategoryModel]]:
        stmt = (
            select(OffenseTypeModel, OffenseCategoryModel)
            .join(OffenseCategoryModel, OffenseCategoryModel.id == OffenseTypeModel.category_id)
            .order_by(OffenseTypeModel.code)
        )
        return list((await self._session.execute(stmt)).all())

    async def get_offense_by_code(self, code: str) -> OffenseTypeModel | None:
        return await self._session.scalar(
            select(OffenseTypeModel).where(OffenseTypeModel.code == code)
        )

    async def get_station_by_code(self, code: str) -> PoliceStationModel | None:
        return await self._session.scalar(
            select(PoliceStationModel).where(PoliceStationModel.code == code)
        )

    async def create_batch(self, batch: IngestBatchModel) -> IngestBatchModel:
        self._session.add(batch)
        await self._session.flush()
        return batch

    async def get_batch(self, batch_id: UUID) -> IngestBatchModel | None:
        return await self._session.get(IngestBatchModel, batch_id)

    async def add_incident(self, incident: IncidentModel) -> IncidentModel:
        self._session.add(incident)
        await self._session.flush()
        return incident

    async def spatial_bbox(
        self,
        *,
        min_lon: float,
        min_lat: float,
        max_lon: float,
        max_lat: float,
        district_ids: list[UUID] | None,
        station_ids: list[UUID] | None,
        occurred_from: datetime | None,
        occurred_to: datetime | None,
        offense_type_id: UUID | None,
        limit: int,
    ) -> list[tuple[IncidentModel, OffenseTypeModel, float, float]]:
        envelope = func.ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
        stmt = self._apply_auth_scope(
            self._base_stmt(),
            district_ids=district_ids,
            station_ids=station_ids,
        ).where(func.ST_Intersects(cast(IncidentModel.location, Geometry), envelope))
        if occurred_from is not None:
            stmt = stmt.where(IncidentModel.occurred_at >= occurred_from)
        if occurred_to is not None:
            stmt = stmt.where(IncidentModel.occurred_at < occurred_to)
        if offense_type_id is not None:
            stmt = stmt.where(IncidentModel.offense_type_id == offense_type_id)
        stmt = stmt.order_by(IncidentModel.occurred_at.desc()).limit(limit)
        rows = await self._session.execute(stmt)
        return [(r[0], r[1], float(r[2]), float(r[3])) for r in rows.all()]

    async def spatial_radius(
        self,
        *,
        lon: float,
        lat: float,
        radius_m: float,
        district_ids: list[UUID] | None,
        station_ids: list[UUID] | None,
        occurred_from: datetime | None,
        occurred_to: datetime | None,
        offense_type_id: UUID | None,
        limit: int,
    ) -> list[tuple[IncidentModel, OffenseTypeModel, float, float]]:
        stmt = self._apply_auth_scope(
            self._base_stmt(),
            district_ids=district_ids,
            station_ids=station_ids,
        ).where(
            text(
                "ST_DWithin(incidents.location, "
                "ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography, :radius_m)"
            ).bindparams(lon=lon, lat=lat, radius_m=radius_m)
        )
        if occurred_from is not None:
            stmt = stmt.where(IncidentModel.occurred_at >= occurred_from)
        if occurred_to is not None:
            stmt = stmt.where(IncidentModel.occurred_at < occurred_to)
        if offense_type_id is not None:
            stmt = stmt.where(IncidentModel.offense_type_id == offense_type_id)
        stmt = stmt.order_by(IncidentModel.occurred_at.desc()).limit(limit)
        rows = await self._session.execute(stmt)
        return [(r[0], r[1], float(r[2]), float(r[3])) for r in rows.all()]
