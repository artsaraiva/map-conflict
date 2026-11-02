"""Map points: which Events the map shows, and what each point says about its Reports."""

from datetime import datetime, timedelta, timezone

import pytest

from backend.api.events import map_points
from backend.models.event import Article, Event, EventType, SeverityLevel

pytestmark = pytest.mark.asyncio

NOW = datetime.utcnow()


async def add_event(session, title, *, hours_ago=1, lat=15.0, lng=42.0, reports=(), **fields):
    """Store an Event created `hours_ago`, with one Report per (source, image_url) pair."""
    event = Event(
        title=title,
        location_name="Red Sea",
        latitude=lat,
        longitude=lng,
        created_at=NOW - timedelta(hours=hours_ago),
        **fields,
    )
    session.add(event)
    await session.flush()
    for i, (source, image_url) in enumerate(reports):
        session.add(
            Article(
                url=f"https://{source}/{title}/{i}",
                title=title,
                source=source,
                image_url=image_url,
                event_id=event.id,
            )
        )
    await session.commit()
    return event


def titles(points):
    return [p.title for p in points]


async def test_time_window_excludes_events_created_before_it(session):
    await add_event(session, "recent", hours_ago=2)
    await add_event(session, "old", hours_ago=80)

    assert titles(await map_points(session, since_hours=72)) == ["recent"]


async def test_bounding_box_keeps_events_inside_it(session):
    await add_event(session, "inside", lat=15.0, lng=42.0)
    await add_event(session, "outside", lat=48.0, lng=37.0)

    points = await map_points(session, since_hours=72, bbox=(10.0, 20.0, 35.0, 45.0))

    assert titles(points) == ["inside"]
    assert sorted(titles(await map_points(session, since_hours=72, bbox=None))) == ["inside", "outside"]


async def test_event_type_severity_and_theater_filters_take_one_or_several_values(session):
    await add_event(session, "strike", event_type=EventType.CONFLICT,
                    severity=SeverityLevel.HIGH, theater="Red Sea")
    await add_event(session, "blockade", event_type=EventType.NAVAL_BLOCKADE,
                    severity=SeverityLevel.CRITICAL, theater="Taiwan Strait")
    await add_event(session, "talks", event_type=EventType.DIPLOMATIC_TENSION,
                    severity=SeverityLevel.LOW, theater="Gaza")

    async def shown(**filters):
        return sorted(titles(await map_points(session, since_hours=72, **filters)))

    assert await shown(event_types=("conflict",)) == ["strike"]
    assert await shown(event_types=("conflict", "naval_blockade")) == ["blockade", "strike"]
    assert await shown(severities=("low",)) == ["talks"]
    assert await shown(severities=("low", "critical")) == ["blockade", "talks"]
    assert await shown(theaters=("Gaza",)) == ["talks"]
    assert await shown(theaters=("Gaza", "Red Sea")) == ["strike", "talks"]


async def test_point_counts_reports_and_lists_each_source_once_alphabetically(session):
    await add_event(session, "strike", reports=[
        ("reuters.com", None),
        ("bbc.co.uk", None),
        ("t.me/rnintel", None),
        ("bbc.co.uk", None),
    ])

    [point] = await map_points(session, since_hours=72)

    assert point.article_count == 4
    assert point.sources == ["bbc.co.uk", "reuters.com", "t.me/rnintel"]


async def test_point_image_is_from_the_earliest_report_that_has_one(session):
    await add_event(session, "strike", reports=[
        ("reuters.com", None),
        ("bbc.co.uk", "https://img/first.jpg"),
        ("apnews.com", "https://img/second.jpg"),
    ])

    [point] = await map_points(session, since_hours=72)

    assert point.image_url == "https://img/first.jpg"


async def test_event_without_reports_gives_an_empty_point(session):
    await add_event(session, "unreported")

    [point] = await map_points(session, since_hours=72)

    assert (point.article_count, point.sources, point.image_url) == (0, [], None)


async def test_points_are_newest_first(session):
    await add_event(session, "middle", hours_ago=5)
    await add_event(session, "newest", hours_ago=1)
    await add_event(session, "oldest", hours_ago=10)

    assert titles(await map_points(session, since_hours=72)) == ["newest", "middle", "oldest"]


async def test_point_time_is_sent_as_utc(session):
    event = await add_event(session, "strike", hours_ago=3)

    [point] = await map_points(session, since_hours=72)
    sent = point.model_dump(mode="json")["created_at"]

    assert sent.endswith(("Z", "+00:00"))
    assert datetime.fromisoformat(sent) == event.created_at.replace(tzinfo=timezone.utc)
