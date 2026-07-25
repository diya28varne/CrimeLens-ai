"""Criminal network service."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from crimelens_domain.identity import AuthContext
from crimelens_domain.shared.errors import NotFoundError

from app.infra.db.models import PersonLinkModel, PersonModel
from app.modules.network.schemas import (
    GraphMeta,
    NamedCount,
    NetworkEdge,
    NetworkGraphData,
    NetworkNode,
    PersonDetail,
    RepeatOffenderRow,
)


class NetworkService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def graph(
        self,
        ctx: AuthContext,
        *,
        person_id: UUID | None = None,
        min_weight: float = 0.0,
        limit_nodes: int = 50,
    ) -> NetworkGraphData:
        _ = ctx
        persons_stmt = select(PersonModel).where(PersonModel.deleted_at.is_(None))
        if person_id:
            # ego: include linked neighbors
            link_stmt = select(PersonLinkModel).where(
                or_(
                    PersonLinkModel.person_a_id == person_id,
                    PersonLinkModel.person_b_id == person_id,
                )
            )
            links = (await self._session.execute(link_stmt)).scalars().all()
            ids = {person_id}
            for link in links:
                ids.add(link.person_a_id)
                ids.add(link.person_b_id)
            persons_stmt = persons_stmt.where(PersonModel.id.in_(ids))
        persons_stmt = persons_stmt.limit(limit_nodes)
        persons = (await self._session.execute(persons_stmt)).scalars().all()
        person_ids = {p.id for p in persons}

        links_stmt = select(PersonLinkModel).where(
            PersonLinkModel.person_a_id.in_(person_ids),
            PersonLinkModel.person_b_id.in_(person_ids),
            PersonLinkModel.weight >= min_weight,
        )
        links = (await self._session.execute(links_stmt)).scalars().all()

        nodes = [
            NetworkNode(
                id=str(p.id),
                label=p.alias or p.full_name,
                is_repeat_offender=p.is_repeat_offender,
                incident_count=int((p.properties or {}).get("incident_count", 0)),
                risk_flags=p.risk_flags or {},
            )
            for p in persons
        ]
        edges = [
            NetworkEdge(
                id=str(e.id),
                source=str(e.person_a_id),
                target=str(e.person_b_id),
                link_type=e.link_type.value,
                origin=e.origin.value,
                weight=e.weight,
            )
            for e in links
        ]
        return NetworkGraphData(
            nodes=nodes,
            edges=edges,
            meta=GraphMeta(
                truncated=len(persons) >= limit_nodes,
                node_count=len(nodes),
                edge_count=len(edges),
            ),
        )

    async def person(self, ctx: AuthContext, person_id: UUID) -> PersonDetail:
        _ = ctx
        person = await self._session.get(PersonModel, person_id)
        if person is None or person.deleted_at is not None:
            raise NotFoundError("Person not found")
        link_count = await self._session.scalar(
            select(func.count())
            .select_from(PersonLinkModel)
            .where(
                or_(
                    PersonLinkModel.person_a_id == person_id,
                    PersonLinkModel.person_b_id == person_id,
                )
            )
        )
        return PersonDetail(
            id=person.id,
            full_name=person.full_name,
            alias=person.alias,
            is_repeat_offender=person.is_repeat_offender,
            incident_count=int((person.properties or {}).get("incident_count", 0)),
            links_out_count=int(link_count or 0),
            risk_flags=person.risk_flags or {},
        )

    async def repeat_offenders(self, ctx: AuthContext, *, limit: int = 20) -> list[RepeatOffenderRow]:
        _ = ctx
        persons = (
            await self._session.execute(
                select(PersonModel)
                .where(
                    PersonModel.deleted_at.is_(None),
                    PersonModel.is_repeat_offender.is_(True),
                )
                .order_by(PersonModel.full_name)
                .limit(limit)
            )
        ).scalars().all()
        rows: list[RepeatOffenderRow] = []
        for p in persons:
            props = p.properties or {}
            mix = [
                NamedCount(key=k, name=k, count=int(v))
                for k, v in (props.get("offense_mix") or {}).items()
            ]
            rows.append(
                RepeatOffenderRow(
                    person_id=p.id,
                    full_name=p.full_name,
                    incident_count=int(props.get("incident_count", 0)),
                    offense_mix=mix,
                    last_occurred_at=None,
                    score=float(props.get("score", 0.5)),
                )
            )
        rows.sort(key=lambda r: r.score, reverse=True)
        return rows
