"""Pressure per Theater: what the API serves for the current window and the one before it."""

import os
import tempfile
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("MEDIA_DIR", tempfile.mkdtemp())  # the app creates its media directory on import
from backend.api.main import app  # noqa: E402
from backend.core.database import get_db  # noqa: E402
from backend.models.event import Event, SeverityLevel  # noqa: E402

pytestmark = pytest.mark.asyncio

NOW = datetime.utcnow()


@pytest_asyncio.fixture
async def client(session):
    async def test_db():
        yield session

    app.dependency_overrides[get_db] = test_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


async def add_event(session, theater, severity, confidence, *, hours_ago=1, updated_hours_ago=None):
    session.add(Event(
        title="strike", location_name="somewhere", latitude=0.0, longitude=0.0,
        theater=theater, severity=severity, confidence_score=confidence,
        created_at=NOW - timedelta(hours=hours_ago),
        updated_at=NOW - timedelta(hours=updated_hours_ago if updated_hours_ago is not None else hours_ago),
    ))
    await session.commit()


async def pressure_by_theater(client, **params):
    response = await client.get("/api/pressure", params=params)
    assert response.status_code == 200
    return {f["properties"]["name"]: f["properties"] for f in response.json()["features"]}


async def test_pressure_sums_severity_weight_times_confidence_per_theater(session, client):
    await add_event(session, "Gaza", SeverityLevel.HIGH, 0.4)       # 4 × 0.4 = 1.6
    await add_event(session, "Gaza", SeverityLevel.LOW, 1.0)        # 1 × 1.0 = 1.0
    await add_event(session, "Sudan", SeverityLevel.CRITICAL, 0.2)  # 8 × 0.2 = 1.6
    await add_event(session, "Sudan", SeverityLevel.MEDIUM, 0.6)    # 2 × 0.6 = 1.2

    theaters = await pressure_by_theater(client)

    assert theaters["Gaza"]["pressure"] == pytest.approx(2.6)
    assert theaters["Sudan"]["pressure"] == pytest.approx(2.8)


async def test_events_outside_the_window_or_every_theater_do_not_count(session, client):
    await add_event(session, "Gaza", SeverityLevel.HIGH, 1.0, hours_ago=1)
    await add_event(session, "Gaza", SeverityLevel.CRITICAL, 1.0, hours_ago=30)
    await add_event(session, "Gaza", SeverityLevel.CRITICAL, 1.0, hours_ago=60)
    await add_event(session, None, SeverityLevel.CRITICAL, 1.0, hours_ago=1)
    # Corroborated an hour ago, but created before the window: it counts where it was created
    await add_event(session, "Sudan", SeverityLevel.HIGH, 1.0, hours_ago=30, updated_hours_ago=1)

    theaters = await pressure_by_theater(client)

    assert (theaters["Gaza"]["pressure"], theaters["Gaza"]["previous_pressure"]) == (4.0, 8.0)
    assert (theaters["Sudan"]["pressure"], theaters["Sudan"]["previous_pressure"]) == (0.0, 4.0)
    assert sum(t["pressure"] for t in theaters.values()) == 4.0


async def test_window_length_is_set_with_window_hours(session, client):
    await add_event(session, "Gaza", SeverityLevel.HIGH, 1.0, hours_ago=1)
    await add_event(session, "Gaza", SeverityLevel.LOW, 1.0, hours_ago=5)

    theaters = await pressure_by_theater(client, window_hours=3)

    assert (theaters["Gaza"]["pressure"], theaters["Gaza"]["previous_pressure"]) == (4.0, 1.0)


async def test_every_theater_is_served_with_its_polygon_even_at_zero(session, client):
    response = await client.get("/api/pressure")
    collection = response.json()

    assert collection["type"] == "FeatureCollection"
    assert len(collection["features"]) == 15
    gaza = next(f for f in collection["features"] if f["properties"]["name"] == "Gaza")
    assert gaza["geometry"]["type"] == "Polygon"
    assert gaza["properties"] == {"name": "Gaza", "pressure": 0.0, "previous_pressure": 0.0, "escalating": False}


async def test_a_theater_rising_from_nothing_by_one_critical_event_is_escalating(session, client):
    await add_event(session, "Gaza", SeverityLevel.CRITICAL, 0.2)
    await add_event(session, "Sudan", SeverityLevel.HIGH, 0.2)

    theaters = await pressure_by_theater(client)

    assert theaters["Gaza"]["escalating"] is True
    assert theaters["Sudan"]["escalating"] is False
