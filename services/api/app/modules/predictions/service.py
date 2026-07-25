"""Prediction / hotspot application service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from crimelens_domain.identity import AuthContext
from crimelens_domain.shared.errors import NotFoundError

from app.infra.db.models import (
    ExplanationArtifactModel,
    HotspotFeatureModel,
    HotspotRunModel,
    ModelRegistryModel,
    PredictionMetric,
    PredictionRunModel,
    PredictionValueModel,
)
from app.modules.predictions.schemas import (
    CurrentPredictionsData,
    ExplanationData,
    FeatureContribution,
    FeatureImportance,
    HotspotFeatureOut,
    HotspotRunSummary,
    HotspotsCurrentData,
    ModelCard,
    PredictionRunSummary,
    PredictionValueOut,
)


class PredictionService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _banner(self, generated_at: datetime) -> str:
        age = datetime.now(UTC) - (
            generated_at if generated_at.tzinfo else generated_at.replace(tzinfo=UTC)
        )
        if age > timedelta(days=7):
            return "stale"
        return "fresh"

    def _run_summary(self, run: PredictionRunModel, model: ModelRegistryModel) -> PredictionRunSummary:
        return PredictionRunSummary(
            id=run.id,
            model_code=model.model_code,
            model_version=model.model_version,
            task=model.task.value,
            metric=run.metric.value,
            scope_type=run.scope_type.value,
            horizon_start=run.horizon_start,
            horizon_end=run.horizon_end,
            generated_at=run.generated_at,
            is_current=run.is_current,
            status_banner=self._banner(run.generated_at),
        )

    def _value_out(self, row: PredictionValueModel) -> PredictionValueOut:
        scope_type = "station" if row.station_id else "district" if row.district_id else "unknown"
        return PredictionValueOut(
            id=row.id,
            scope={
                "type": scope_type,
                "district_id": str(row.district_id) if row.district_id else None,
                "station_id": str(row.station_id) if row.station_id else None,
            },
            value=row.value,
            lower_bound=row.lower_bound,
            upper_bound=row.upper_bound,
            occurs_on=row.occurs_on,
            properties=row.properties or {},
        )

    async def list_runs(self, ctx: AuthContext, *, is_current: bool | None = None) -> list[PredictionRunSummary]:
        _ = ctx
        stmt = (
            select(PredictionRunModel, ModelRegistryModel)
            .join(ModelRegistryModel, ModelRegistryModel.id == PredictionRunModel.model_id)
            .order_by(PredictionRunModel.generated_at.desc())
        )
        if is_current is not None:
            stmt = stmt.where(PredictionRunModel.is_current.is_(is_current))
        rows = (await self._session.execute(stmt)).all()
        return [self._run_summary(run, model) for run, model in rows]

    async def list_models(self, ctx: AuthContext) -> list[ModelCard]:
        _ = ctx
        rows = (
            await self._session.execute(
                select(ModelRegistryModel).order_by(ModelRegistryModel.model_code, ModelRegistryModel.model_version)
            )
        ).scalars().all()
        out: list[ModelCard] = []
        for m in rows:
            train = None
            if m.train_window_start and m.train_window_end:
                train = {"start": m.train_window_start.isoformat(), "end": m.train_window_end.isoformat()}
            out.append(
                ModelCard(
                    model_code=m.model_code,
                    model_version=m.model_version,
                    task=m.task.value,
                    algorithm=m.algorithm,
                    status=m.status.value,
                    metrics=m.metrics or {},
                    train_window=train,
                )
            )
        return out

    async def current(
        self,
        ctx: AuthContext,
        *,
        metric: PredictionMetric = PredictionMetric.risk_score,
        district_id: UUID | None = None,
        station_id: UUID | None = None,
        top_n: int = 20,
    ) -> CurrentPredictionsData:
        _ = ctx
        stmt = (
            select(PredictionRunModel, ModelRegistryModel)
            .join(ModelRegistryModel, ModelRegistryModel.id == PredictionRunModel.model_id)
            .where(PredictionRunModel.is_current.is_(True), PredictionRunModel.metric == metric)
            .order_by(PredictionRunModel.generated_at.desc())
            .limit(1)
        )
        row = (await self._session.execute(stmt)).first()
        if not row:
            return CurrentPredictionsData(run=None, values=[])
        run, model = row
        vstmt = (
            select(PredictionValueModel)
            .where(PredictionValueModel.prediction_run_id == run.id)
            .order_by(PredictionValueModel.value.desc())
            .limit(top_n)
        )
        if district_id:
            vstmt = vstmt.where(PredictionValueModel.district_id == district_id)
        if station_id:
            vstmt = vstmt.where(PredictionValueModel.station_id == station_id)
        values = (await self._session.execute(vstmt)).scalars().all()
        return CurrentPredictionsData(
            run=self._run_summary(run, model),
            values=[self._value_out(v) for v in values],
        )

    async def explanation(self, ctx: AuthContext, value_id: UUID) -> ExplanationData:
        _ = ctx
        value = await self._session.get(PredictionValueModel, value_id)
        if value is None:
            raise NotFoundError("Prediction value not found", details={"code": "NOT_FOUND"})
        art = await self._session.scalar(
            select(ExplanationArtifactModel).where(
                ExplanationArtifactModel.prediction_value_id == value_id
            )
        )
        if art is None:
            raise NotFoundError(
                "Explanation unavailable",
                details={"code": "EXPLANATION_UNAVAILABLE"},
            )
        run = await self._session.get(PredictionRunModel, value.prediction_run_id)
        model = await self._session.get(ModelRegistryModel, run.model_id) if run else None
        model_version = (
            f"{model.model_code}@{model.model_version}" if model else "unknown"
        )
        global_imp = [
            FeatureImportance(feature=i["feature"], importance=float(i["importance"]))
            for i in (art.shap_global or {}).get("features", [])
        ]
        local = [
            FeatureContribution(
                feature=c["feature"],
                value=c.get("value"),
                contribution=float(c["contribution"]),
            )
            for c in (art.shap_local or {}).get("contributions", [])
        ]
        base = float((art.shap_local or {}).get("base_value", 0.4))
        return ExplanationData(
            prediction_value_id=value_id,
            model_version=model_version,
            base_value=base,
            output_value=value.value,
            global_importance=global_imp,
            local_contributions=local,
            summary_text=art.summary_text,
        )

    async def hotspots_current(
        self,
        ctx: AuthContext,
        *,
        district_id: UUID | None = None,
        limit: int = 20,
    ) -> HotspotsCurrentData:
        _ = ctx
        stmt = select(HotspotRunModel).where(HotspotRunModel.is_current.is_(True))
        if district_id:
            stmt = stmt.where(HotspotRunModel.district_id == district_id)
        stmt = stmt.order_by(HotspotRunModel.created_at.desc()).limit(1)
        run = await self._session.scalar(stmt)
        if run is None:
            return HotspotsCurrentData(run=None, features=[])
        features = (
            await self._session.execute(
                select(HotspotFeatureModel)
                .where(HotspotFeatureModel.hotspot_run_id == run.id)
                .order_by(HotspotFeatureModel.rank.asc())
                .limit(limit)
            )
        ).scalars().all()
        out_features: list[HotspotFeatureOut] = []
        for f in features:
            props = f.properties or {}
            lon = props.get("lon")
            lat = props.get("lat")
            out_features.append(
                HotspotFeatureOut(
                    id=f.id,
                    rank=f.rank,
                    score=f.score,
                    incident_count=f.incident_count,
                    centroid={"type": "Point", "coordinates": [lon, lat]} if lon is not None else {},
                    properties=props,
                )
            )
        return HotspotsCurrentData(
            run=HotspotRunSummary(
                id=run.id,
                method=run.method.value,
                model_version=run.model_version,
                window_start=run.window_start,
                window_end=run.window_end,
                is_current=run.is_current,
            ),
            features=out_features,
        )
