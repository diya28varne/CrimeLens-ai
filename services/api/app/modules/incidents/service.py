"""Incident application service."""

from __future__ import annotations

import base64
import json
import uuid
from datetime import UTC, datetime
from uuid import UUID

from crimelens_domain.identity import AuthContext
from crimelens_domain.identity.permissions import INCIDENT_INGEST
from crimelens_domain.shared.errors import ForbiddenError, NotFoundError, ValidationAppError

from app.infra.db.geo import parse_bbox, point_geography
from app.infra.db.models import (
    IncidentModel,
    IncidentSource,
    IncidentStatus,
    IngestBatchModel,
    SeverityLevel,
)
from app.modules.incidents.repository import IncidentRepository
from app.modules.incidents.schemas import (
    GeoPoint,
    IncidentDetail,
    IncidentIngestData,
    IncidentIngestRequest,
    IncidentSummary,
    IngestBatchStatus,
    IngestError,
    OffenseTypeOut,
    OffenseTypeRef,
    PageMeta,
)


class IncidentService:
    def __init__(self, repo: IncidentRepository) -> None:
        self._repo = repo

    def _scope(self, ctx: AuthContext) -> tuple[list[UUID] | None, list[UUID] | None]:
        if ctx.is_superuser:
            return None, None
        return list(ctx.allowed_district_ids), list(ctx.allowed_station_ids)

    def _ensure_can_read(self, ctx: AuthContext, district_id: UUID, station_id: UUID) -> None:
        if ctx.is_superuser:
            return
        if district_id in ctx.allowed_district_ids:
            return
        if station_id in ctx.allowed_station_ids:
            return
        raise NotFoundError("Incident not found")

    @staticmethod
    def _encode_cursor(occurred_at: datetime, incident_id: UUID) -> str:
        payload = {"o": occurred_at.isoformat(), "i": str(incident_id)}
        return base64.urlsafe_b64encode(json.dumps(payload).encode()).decode()

    @staticmethod
    def _decode_cursor(cursor: str) -> tuple[datetime, UUID]:
        try:
            raw = json.loads(base64.urlsafe_b64decode(cursor.encode()).decode())
            return datetime.fromisoformat(raw["o"]), UUID(raw["i"])
        except Exception as exc:  # noqa: BLE001
            raise ValidationAppError("Invalid cursor") from exc

    def _to_summary(
        self,
        incident: IncidentModel,
        offense: object,
        lon: float,
        lat: float,
    ) -> IncidentSummary:
        return IncidentSummary(
            id=incident.id,
            external_ref=incident.external_ref,
            offense_type=OffenseTypeRef(id=offense.id, code=offense.code, name=offense.name),
            district_id=incident.district_id,
            station_id=incident.station_id,
            status=incident.status.value,
            severity=incident.severity.value,
            occurred_at=incident.occurred_at,
            location=GeoPoint(lon=lon, lat=lat),
            title=incident.title,
        )

    async def list_incidents(
        self,
        ctx: AuthContext,
        *,
        district_id: UUID | None,
        station_id: UUID | None,
        offense_type_id: UUID | None,
        status: str | None,
        severity: str | None,
        occurred_from: datetime | None,
        occurred_to: datetime | None,
        q: str | None,
        limit: int,
        cursor: str | None,
    ) -> tuple[list[IncidentSummary], PageMeta]:
        district_ids, station_ids = self._scope(ctx)
        cursor_occurred_at = cursor_id = None
        if cursor:
            cursor_occurred_at, cursor_id = self._decode_cursor(cursor)
        rows = await self._repo.list_incidents(
            district_ids=district_ids,
            station_ids=station_ids,
            district_id=district_id,
            station_id=station_id,
            offense_type_id=offense_type_id,
            status=status,
            severity=severity,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
            q=q,
            limit=limit + 1,
            cursor_occurred_at=cursor_occurred_at,
            cursor_id=cursor_id,
        )
        has_more = len(rows) > limit
        rows = rows[:limit]
        data = [self._to_summary(i, o, lon, lat) for i, o, lon, lat in rows]
        next_cursor = None
        if has_more and rows:
            last = rows[-1][0]
            next_cursor = self._encode_cursor(last.occurred_at, last.id)
        return data, PageMeta(next_cursor=next_cursor, limit=limit)

    async def get_incident(self, ctx: AuthContext, incident_id: UUID) -> IncidentDetail:
        row = await self._repo.get_incident(incident_id)
        if row is None:
            raise NotFoundError("Incident not found")
        incident, offense, lon, lat = row
        self._ensure_can_read(ctx, incident.district_id, incident.station_id)
        summary = self._to_summary(incident, offense, lon, lat)
        return IncidentDetail(
            **summary.model_dump(),
            description=incident.description,
            reported_at=incident.reported_at,
            registered_at=incident.registered_at,
            address_text=incident.address_text,
            source=incident.source.value,
            properties=incident.properties or {},
        )

    async def list_offense_types(self) -> list[OffenseTypeOut]:
        rows = await self._repo.list_offense_types()
        return [
            OffenseTypeOut(
                id=offense.id,
                code=offense.code,
                name=offense.name,
                category=category.code,
                default_severity=offense.default_severity.value,
            )
            for offense, category in rows
        ]

    async def ingest(
        self, ctx: AuthContext, body: IncidentIngestRequest
    ) -> IncidentIngestData:
        if not ctx.has_permission(INCIDENT_INGEST) and not ctx.is_superuser:
            raise ForbiddenError("Missing permission: incident:ingest")

        errors: list[IngestError] = []
        accepted = 0
        batch: IngestBatchModel | None = None
        if not body.dry_run:
            batch = await self._repo.create_batch(
                IngestBatchModel(
                    id=uuid.uuid4(),
                    source=IncidentSource.api_ingest,
                    row_count=len(body.rows),
                    success_count=0,
                    error_count=0,
                    created_by=ctx.user_id,
                    errors=[],
                )
            )

        for idx, row in enumerate(body.rows):
            try:
                offense = await self._repo.get_offense_by_code(row.offense_code)
                if offense is None:
                    raise ValidationAppError(f"Unknown offense_code: {row.offense_code}")
                station = await self._repo.get_station_by_code(row.station_code)
                if station is None:
                    raise ValidationAppError(f"Unknown station_code: {row.station_code}")
                if not ctx.is_superuser and station.district_id not in ctx.allowed_district_ids:
                    if station.id not in ctx.allowed_station_ids:
                        raise ForbiddenError("Station outside jurisdiction")

                status = IncidentStatus(row.status) if row.status else IncidentStatus.reported
                severity = (
                    SeverityLevel(row.severity)
                    if row.severity
                    else offense.default_severity
                )
                if body.dry_run:
                    accepted += 1
                    continue

                assert batch is not None
                await self._repo.add_incident(
                    IncidentModel(
                        id=uuid.uuid4(),
                        external_ref=row.external_ref,
                        offense_type_id=offense.id,
                        district_id=station.district_id,
                        station_id=station.id,
                        status=status,
                        severity=severity,
                        source=IncidentSource.api_ingest,
                        occurred_at=row.occurred_at,
                        title=row.title,
                        description=row.description,
                        location=point_geography(row.lon, row.lat),
                        properties=row.properties,
                        ingest_batch_id=batch.id,
                        created_by=ctx.user_id,
                    )
                )
                accepted += 1
            except (ValidationAppError, ForbiddenError, ValueError) as exc:
                errors.append(
                    IngestError(row=idx, code=getattr(exc, "code", "VALIDATION_ERROR"), message=str(exc))
                )

        if batch is not None:
            batch.success_count = accepted
            batch.error_count = len(errors)
            batch.errors = [e.model_dump() for e in errors]
            batch.finished_at = datetime.now(UTC)

        return IncidentIngestData(
            batch_id=batch.id if batch else None,
            accepted=accepted,
            rejected=len(errors),
            errors=errors,
        )

    async def get_batch(self, batch_id: UUID) -> IngestBatchStatus:
        batch = await self._repo.get_batch(batch_id)
        if batch is None:
            raise NotFoundError("Ingest batch not found")
        return IngestBatchStatus(
            id=batch.id,
            source=batch.source.value,
            row_count=batch.row_count,
            success_count=batch.success_count,
            error_count=batch.error_count,
            started_at=batch.started_at,
            finished_at=batch.finished_at,
            errors=batch.errors or [],
        )

    async def spatial_features(
        self,
        ctx: AuthContext,
        *,
        bbox: str | None,
        lon: float | None,
        lat: float | None,
        radius_m: float | None,
        occurred_from: datetime | None,
        occurred_to: datetime | None,
        offense_type_id: UUID | None,
        limit: int,
    ) -> dict:
        district_ids, station_ids = self._scope(ctx)
        if bbox:
            min_lon, min_lat, max_lon, max_lat = parse_bbox(bbox)
            rows = await self._repo.spatial_bbox(
                min_lon=min_lon,
                min_lat=min_lat,
                max_lon=max_lon,
                max_lat=max_lat,
                district_ids=district_ids,
                station_ids=station_ids,
                occurred_from=occurred_from,
                occurred_to=occurred_to,
                offense_type_id=offense_type_id,
                limit=limit,
            )
        elif lon is not None and lat is not None and radius_m is not None:
            rows = await self._repo.spatial_radius(
                lon=lon,
                lat=lat,
                radius_m=radius_m,
                district_ids=district_ids,
                station_ids=station_ids,
                occurred_from=occurred_from,
                occurred_to=occurred_to,
                offense_type_id=offense_type_id,
                limit=limit,
            )
        else:
            raise ValidationAppError("Provide bbox or lon/lat/radius_m")

        features = []
        for incident, offense, x, y in rows:
            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [x, y]},
                    "properties": {
                        "id": str(incident.id),
                        "offense_code": offense.code,
                        "severity": incident.severity.value,
                        "occurred_at": incident.occurred_at.isoformat(),
                        "station_id": str(incident.station_id),
                    },
                }
            )
        return {"type": "FeatureCollection", "features": features}
