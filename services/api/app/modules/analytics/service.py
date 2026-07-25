"""Socio-economic ↔ crime correlation application service."""

from __future__ import annotations

from uuid import UUID

from crimelens_domain.identity import AuthContext
from crimelens_domain.shared.errors import ValidationAppError
from crimelens_domain.socioeconomics import (
    INDICATOR_CATALOG,
    interpret_correlation,
    pearson_correlation,
)

from app.modules.analytics.repository import SocioEconomicRepository
from app.modules.analytics.schemas import (
    CorrelationResult,
    CorrelationSummary,
    CrimeMetricRow,
    IndicatorRow,
    ScatterPoint,
)


class SocioEconomicService:
    def __init__(self, repo: SocioEconomicRepository) -> None:
        self._repo = repo

    def _scoped_district_ids(self, ctx: AuthContext) -> list[UUID] | None:
        """None means unrestricted (superuser); else explicit allow-list."""
        if ctx.is_superuser:
            return None
        return list(ctx.allowed_district_ids)

    async def resolve_year(self, year: int | None) -> int:
        if year is not None:
            return year
        latest = await self._repo.latest_indicator_year()
        if latest is None:
            raise ValidationAppError("No socio-economic data available yet")
        return latest

    async def list_indicators(
        self,
        ctx: AuthContext,
        *,
        year: int | None,
        district_id: UUID | None,
        indicator_code: str | None,
    ) -> list[IndicatorRow]:
        resolved_year = await self.resolve_year(year)
        if indicator_code and indicator_code not in INDICATOR_CATALOG:
            raise ValidationAppError(
                f"Unknown indicator_code: {indicator_code}",
                details={"allowed": list(INDICATOR_CATALOG.keys())},
            )
        scoped = self._scoped_district_ids(ctx)
        if district_id is not None:
            if scoped is not None and district_id not in scoped:
                return []
            district_ids = [district_id]
        else:
            district_ids = scoped

        rows = await self._repo.list_indicators(
            year=resolved_year,
            district_ids=district_ids,
            indicator_code=indicator_code,
        )
        return [
            IndicatorRow(
                district_id=district.id,
                district_code=district.code,
                district_name=district.name,
                year=ind.year,
                indicator_code=ind.indicator_code,
                value=ind.value,
                unit=ind.unit,
                source=ind.source,
            )
            for ind, district in rows
        ]

    async def list_crime_metrics(
        self,
        ctx: AuthContext,
        *,
        year: int | None,
        district_id: UUID | None,
    ) -> list[CrimeMetricRow]:
        resolved_year = await self.resolve_year(year)
        scoped = self._scoped_district_ids(ctx)
        if district_id is not None:
            if scoped is not None and district_id not in scoped:
                return []
            district_ids = [district_id]
        else:
            district_ids = scoped

        rows = await self._repo.list_crime_metrics(year=resolved_year, district_ids=district_ids)
        return [
            CrimeMetricRow(
                district_id=district.id,
                district_code=district.code,
                district_name=district.name,
                year=metric.year,
                incident_count=metric.incident_count,
                crime_rate_per_100k=metric.crime_rate_per_100k,
                high_severity_count=metric.high_severity_count,
            )
            for metric, district in rows
        ]

    async def correlate(
        self,
        ctx: AuthContext,
        *,
        year: int | None,
        indicator_code: str,
        crime_metric: str,
    ) -> CorrelationResult:
        if indicator_code not in INDICATOR_CATALOG:
            raise ValidationAppError(
                f"Unknown indicator_code: {indicator_code}",
                details={"allowed": list(INDICATOR_CATALOG.keys())},
            )
        if crime_metric not in {"crime_rate_per_100k", "incident_count"}:
            raise ValidationAppError("crime_metric must be crime_rate_per_100k or incident_count")

        resolved_year = await self.resolve_year(year)
        scoped = self._scoped_district_ids(ctx)
        indicators = await self._repo.list_indicators(
            year=resolved_year,
            district_ids=scoped,
            indicator_code=indicator_code,
        )
        crimes = await self._repo.list_crime_metrics(year=resolved_year, district_ids=scoped)
        crime_by_district = {district.id: (metric, district) for metric, district in crimes}

        xs: list[float] = []
        ys: list[float] = []
        points: list[ScatterPoint] = []
        for ind, district in indicators:
            pair = crime_by_district.get(district.id)
            if pair is None:
                continue
            metric, _ = pair
            crime_value = (
                metric.crime_rate_per_100k
                if crime_metric == "crime_rate_per_100k"
                else float(metric.incident_count)
            )
            xs.append(float(ind.value))
            ys.append(float(crime_value))
            points.append(
                ScatterPoint(
                    district_id=district.id,
                    district_code=district.code,
                    district_name=district.name,
                    indicator_value=float(ind.value),
                    crime_value=float(crime_value),
                )
            )

        coefficient = pearson_correlation(xs, ys)
        abs_coefficient = abs(coefficient) if coefficient is not None else None
        interpretation = interpret_correlation(coefficient, len(points))
        return CorrelationResult(
            year=resolved_year,
            indicator_code=indicator_code,
            crime_metric=crime_metric,  # type: ignore[arg-type]
            method="pearson",
            coefficient=coefficient,
            abs_coefficient=abs_coefficient,
            sample_size=len(points),
            interpretation=interpretation.value,
            points=points,
        )

    async def rank_correlations(
        self,
        ctx: AuthContext,
        *,
        year: int | None,
        crime_metric: str,
    ) -> list[CorrelationSummary]:
        resolved_year = await self.resolve_year(year)
        codes = await self._repo.indicator_codes_for_year(resolved_year)
        summaries: list[CorrelationSummary] = []
        for code in codes:
            result = await self.correlate(
                ctx,
                year=resolved_year,
                indicator_code=code,
                crime_metric=crime_metric,
            )
            summaries.append(
                CorrelationSummary(
                    year=result.year,
                    indicator_code=result.indicator_code,
                    crime_metric=result.crime_metric,
                    method=result.method,
                    coefficient=result.coefficient,
                    abs_coefficient=result.abs_coefficient,
                    sample_size=result.sample_size,
                    interpretation=result.interpretation,
                )
            )
        summaries.sort(key=lambda row: row.abs_coefficient or -1.0, reverse=True)
        return summaries
