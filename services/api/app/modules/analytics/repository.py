"""Persistence for socio-economic indicators and crime metrics."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db.models import (
    DistrictCrimeMetricModel,
    DistrictModel,
    SocioEconomicIndicatorModel,
)


class SocioEconomicRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_districts(self, allowed_district_ids: tuple[UUID, ...] | None) -> list[DistrictModel]:
        stmt: Select[tuple[DistrictModel]] = select(DistrictModel).where(DistrictModel.is_active.is_(True))
        if allowed_district_ids is not None:
            if not allowed_district_ids:
                return []
            stmt = stmt.where(DistrictModel.id.in_(allowed_district_ids))
        stmt = stmt.order_by(DistrictModel.code)
        result = await self._session.scalars(stmt)
        return list(result.all())

    async def latest_indicator_year(self) -> int | None:
        year = await self._session.scalar(
            select(SocioEconomicIndicatorModel.year)
            .order_by(SocioEconomicIndicatorModel.year.desc())
            .limit(1)
        )
        return int(year) if year is not None else None

    async def list_indicators(
        self,
        *,
        year: int,
        district_ids: list[UUID] | None,
        indicator_code: str | None,
    ) -> list[tuple[SocioEconomicIndicatorModel, DistrictModel]]:
        stmt = (
            select(SocioEconomicIndicatorModel, DistrictModel)
            .join(DistrictModel, DistrictModel.id == SocioEconomicIndicatorModel.district_id)
            .where(SocioEconomicIndicatorModel.year == year)
        )
        if district_ids is not None:
            if not district_ids:
                return []
            stmt = stmt.where(SocioEconomicIndicatorModel.district_id.in_(district_ids))
        if indicator_code:
            stmt = stmt.where(SocioEconomicIndicatorModel.indicator_code == indicator_code)
        stmt = stmt.order_by(DistrictModel.code, SocioEconomicIndicatorModel.indicator_code)
        rows = await self._session.execute(stmt)
        return list(rows.all())

    async def list_crime_metrics(
        self,
        *,
        year: int,
        district_ids: list[UUID] | None,
    ) -> list[tuple[DistrictCrimeMetricModel, DistrictModel]]:
        stmt = (
            select(DistrictCrimeMetricModel, DistrictModel)
            .join(DistrictModel, DistrictModel.id == DistrictCrimeMetricModel.district_id)
            .where(DistrictCrimeMetricModel.year == year)
        )
        if district_ids is not None:
            if not district_ids:
                return []
            stmt = stmt.where(DistrictCrimeMetricModel.district_id.in_(district_ids))
        stmt = stmt.order_by(DistrictModel.code)
        rows = await self._session.execute(stmt)
        return list(rows.all())

    async def indicator_codes_for_year(self, year: int) -> list[str]:
        rows = await self._session.scalars(
            select(SocioEconomicIndicatorModel.indicator_code)
            .where(SocioEconomicIndicatorModel.year == year)
            .distinct()
            .order_by(SocioEconomicIndicatorModel.indicator_code)
        )
        return list(rows.all())
