"""The Links the API serves for one Event, read from either end."""

from datetime import datetime, timedelta

import pytest

from backend.models.event import Event, EventType, Link, SeverityLevel

pytestmark = pytest.mark.asyncio

NOW = datetime.utcnow()


async def add_event(session, title, *, hours_ago):
    event = Event(title=title, location_name="Hodeidah", latitude=14.8, longitude=42.95,
                  event_type=EventType.CONFLICT, severity=SeverityLevel.HIGH, theater="Red Sea and Bab el-Mandeb",
                  confidence_score=0.4, created_at=NOW - timedelta(hours=hours_ago))
    session.add(event)
    await session.flush()
    return event


async def test_links_read_outgoing_from_the_later_event_and_incoming_on_the_earlier_one(session, client):
    strike = await add_event(session, "Houthi missile strike on a tanker", hours_ago=10)
    interception = await add_event(session, "US destroyer intercepts Houthi missiles", hours_ago=8)
    retaliation = await add_event(session, "Coalition strikes Houthi launch sites", hours_ago=2)
    session.add_all([
        Link(from_event_id=interception.id, to_event_id=strike.id, link_type="response_to"),
        Link(from_event_id=retaliation.id, to_event_id=strike.id, link_type="escalation_of"),
    ])
    await session.commit()

    on_strike = (await client.get(f"/api/events/{strike.id}/links")).json()
    on_interception = (await client.get(f"/api/events/{interception.id}/links")).json()

    assert [(e["title"], e["link_type"], e["direction"]) for e in on_strike] == [
        ("Coalition strikes Houthi launch sites", "escalation_of", "incoming"),
        ("US destroyer intercepts Houthi missiles", "response_to", "incoming"),
    ]
    assert on_interception == [{
        "id": strike.id,
        "title": "Houthi missile strike on a tanker",
        "event_type": "conflict",
        "severity": "high",
        "location_name": "Hodeidah",
        "latitude": 14.8,
        "longitude": 42.95,
        "theater": "Red Sea and Bab el-Mandeb",
        "confidence_score": 0.4,
        "created_at": (NOW - timedelta(hours=10)).isoformat() + "Z",
        "link_type": "response_to",
        "direction": "outgoing",
    }]


async def test_links_to_events_created_at_the_same_time_list_the_later_stored_first(session, client):
    strike = await add_event(session, "Houthi missile strike on a tanker", hours_ago=10)
    first = await add_event(session, "US destroyer intercepts Houthi missiles", hours_ago=8)
    second = await add_event(session, "UK frigate intercepts Houthi drones", hours_ago=8)
    session.add_all([
        Link(from_event_id=first.id, to_event_id=strike.id, link_type="response_to"),
        Link(from_event_id=second.id, to_event_id=strike.id, link_type="response_to"),
    ])
    await session.commit()

    on_strike = (await client.get(f"/api/events/{strike.id}/links")).json()

    assert [e["id"] for e in on_strike] == [second.id, first.id]
