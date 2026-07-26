"""Seeded external event markers for Story Playback timeline."""

from __future__ import annotations

from datetime import date, datetime, timedelta, UTC

from app.modules.story.schemas import StoryEvent


def story_events_for_range(from_: date, to: date) -> list[StoryEvent]:
    """Relative demo events anchored to 'today' so they always land in a 90d window."""
    today = datetime.now(UTC).date()
    catalog = [
        StoryEvent(
            id="ev-festival",
            t=today - timedelta(days=38),
            label="Weekend Festival",
            kind="festival",
            detail="Large public gathering near commercial / metro fringe (demo marker).",
        ),
        StoryEvent(
            id="ev-rain",
            t=today - timedelta(days=55),
            label="Heavy Rain",
            kind="weather",
            detail="Weather stress day — useful coincidence check for property crime (demo).",
        ),
        StoryEvent(
            id="ev-holiday",
            t=today - timedelta(days=70),
            label="Public Holiday",
            kind="holiday",
            detail="Reduced daytime foot traffic pattern (demo marker).",
        ),
        StoryEvent(
            id="ev-patrol",
            t=today - timedelta(days=26),
            label="Patrol surge (annotated)",
            kind="intervention",
            detail="Demo annotation: additional evening patrols noted in ops log — not proof of causation.",
        ),
        StoryEvent(
            id="ev-metro",
            t=today - timedelta(days=44),
            label="Metro service disruption",
            kind="infra",
            detail="Alternate-route spillover hypothesis for eastern fringe (demo).",
        ),
    ]
    return [e for e in catalog if from_ <= e.t <= to]
