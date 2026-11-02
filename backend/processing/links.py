"""
Links: proposed from a newly created Event to earlier ones, each with one of three Link types.

`propose_links` picks candidate Events, asks `relate` how the new Event relates to
each, and stores a Link from the new Event to every candidate given a Link type.
"""

import math
from collections.abc import Awaitable, Callable
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.event import Event, Link
from backend.processing.nlp import text_similarity

# Maps candidate Event id to a Link type, or None when the two Events are not linked
Relate = Callable[[Event, list[Event]], Awaitable[dict[int, str | None]]]

LINK_TYPES = {"response_to", "escalation_of", "same_campaign"}

CANDIDATE_WINDOW = timedelta(hours=72)
CANDIDATE_RADIUS_KM = 500
MAX_CANDIDATES = 5


async def propose_links(session: AsyncSession, event: Event, relate: Relate) -> None:
    """Store a Link from `event` to each candidate Event `relate` gives a Link type."""
    candidates = await _candidates(session, event)
    if not candidates:
        return
    answers = await relate(event, candidates)
    for candidate in candidates:
        if answers.get(candidate.id) in LINK_TYPES:
            session.add(Link(from_event_id=event.id, to_event_id=candidate.id,
                             link_type=answers[candidate.id]))


async def _candidates(session: AsyncSession, event: Event) -> list[Event]:
    """Events created in the window before `event` and within the radius of it, most word overlap first."""
    earlier = await session.scalars(
        select(Event)
        .where(Event.id != event.id)
        .where(Event.created_at.between(event.created_at - CANDIDATE_WINDOW, event.created_at))
    )
    # shortcut: distance is checked in Python over every Event in the window; move it into SQL if that gets slow
    nearby = [
        e for e in earlier
        if _distance_km(event.latitude, event.longitude, e.latitude, e.longitude) <= CANDIDATE_RADIUS_KM
    ]
    text = _text(event)
    nearby.sort(key=lambda e: text_similarity(text, _text(e)), reverse=True)
    return nearby[:MAX_CANDIDATES]


def _text(event: Event) -> str:
    return f"{event.title} {event.summary or ''}"


def _distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle (haversine) distance."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((phi2 - phi1) / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(math.radians(lng2 - lng1) / 2) ** 2)
    return 2 * 6371 * math.asin(math.sqrt(a))
