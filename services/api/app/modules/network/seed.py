"""Seed demo criminal network for Bengaluru."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.async_runtime import run_async
from app.infra.db.models import (
    PersonLinkModel,
    PersonLinkOrigin,
    PersonLinkType,
    PersonModel,
)
from app.infra.db.session import get_engine, get_session_factory

PEOPLE = [
    ("P-001", "Ravi Kumar", "Ravi", True, 7, 0.86, {"THEFT": 3, "BURGLARY": 2, "ROBBERY": 2}),
    ("P-002", "Suresh Naik", "Suresh", True, 5, 0.74, {"THEFT": 2, "ASSAULT": 3}),
    ("P-003", "Anita Devi", None, False, 2, 0.41, {"CYBER_FRAUD": 2}),
    ("P-004", "Imran Sheikh", "Imran", True, 4, 0.69, {"ROBBERY": 2, "ASSAULT": 2}),
    ("P-005", "Karthik Rao", None, False, 1, 0.28, {"THEFT": 1}),
    ("P-006", "Meena Joshi", "MJ", False, 3, 0.52, {"CYBER_FRAUD": 2, "THEFT": 1}),
]

# a_ref, b_ref, type, weight
LINKS = [
    ("P-001", "P-002", PersonLinkType.co_accused, 3.0),
    ("P-001", "P-004", PersonLinkType.co_accused, 2.5),
    ("P-002", "P-005", PersonLinkType.associate, 1.5),
    ("P-004", "P-005", PersonLinkType.same_address, 2.0),
    ("P-003", "P-006", PersonLinkType.associate, 1.8),
    ("P-001", "P-006", PersonLinkType.other, 1.0),
]


async def seed_network(session: AsyncSession) -> None:
    existing = await session.scalar(
        select(PersonModel).where(PersonModel.external_ref == "P-001")
    )
    if existing:
        return

    by_ref: dict[str, PersonModel] = {}
    for ref, name, alias, repeat, count, score, mix in PEOPLE:
        person = PersonModel(
            id=uuid.uuid4(),
            external_ref=ref,
            full_name=name,
            alias=alias,
            is_repeat_offender=repeat,
            risk_flags={"watchlist": repeat},
            properties={"incident_count": count, "score": score, "offense_mix": mix},
        )
        session.add(person)
        by_ref[ref] = person
    await session.flush()

    for a_ref, b_ref, link_type, weight in LINKS:
        a = by_ref[a_ref]
        b = by_ref[b_ref]
        # canonical order for uniqueness
        if str(a.id) > str(b.id):
            a, b = b, a
        session.add(
            PersonLinkModel(
                id=uuid.uuid4(),
                person_a_id=a.id,
                person_b_id=b.id,
                link_type=link_type,
                origin=PersonLinkOrigin.derived,
                weight=weight,
            )
        )
    await session.commit()


async def main() -> None:
    engine = get_engine()
    factory = get_session_factory(engine)
    async with factory() as session:
        await seed_network(session)
    await engine.dispose()
    print("Network seed complete.")


if __name__ == "__main__":
    run_async(main())
