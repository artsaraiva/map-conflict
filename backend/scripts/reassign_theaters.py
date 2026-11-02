"""Recompute every stored Event's Theater from its location.

Run once after changing how Theaters are assigned, and after any edit to
`data/theaters.geojson`. Running it again changes nothing.
"""

import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import async_session
from backend.models.event import Event
from backend.processing.theaters import theater_for


async def reassign_theaters(session: AsyncSession) -> int:
    """Set each Event's Theater from its location and commit; returns how many Events changed."""
    # ponytail: loads every Event at once, page through them if the table outgrows memory
    changed = 0
    for event in (await session.scalars(select(Event))).all():
        theater = theater_for(event.latitude, event.longitude)
        if event.theater != theater:
            event.theater = theater
            changed += 1
    await session.commit()
    return changed


async def main() -> None:
    async with async_session() as session:
        print(f"Reassigned the Theater of {await reassign_theaters(session)} Events")


if __name__ == "__main__":
    asyncio.run(main())
