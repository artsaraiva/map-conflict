"""Theater reassignment: stored Events follow the current Theater shapes."""

import pytest
from sqlalchemy import select

from backend.models.event import Event
from backend.scripts.reassign_theaters import reassign_theaters

pytestmark = pytest.mark.asyncio


async def stored_theaters(session):
    rows = await session.execute(select(Event.title, Event.theater).order_by(Event.title))
    return dict(rows.all())


async def test_old_labels_become_named_theaters_or_none_and_a_second_run_changes_nothing(session):
    session.add_all([
        Event(title="gaza", location_name="Gaza City", latitude=31.50, longitude=34.47, theater="Middle East"),
        Event(title="paris", location_name="Paris", latitude=48.86, longitude=2.35, theater="Other"),
    ])
    await session.commit()

    await reassign_theaters(session)
    first = await stored_theaters(session)
    changed = await reassign_theaters(session)

    assert first == {"gaza": "Gaza", "paris": None}
    assert changed == 0
    assert await stored_theaters(session) == first
