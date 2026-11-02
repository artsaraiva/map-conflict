"""
Pressure: how much is going on in each Theater over a window ending now, and whether
it is escalating against the window of the same length just before.

The formula, weights and thresholds are recorded in `docs/adr/0002-pressure-formula.md`.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.models.event import Event, SeverityLevel
from backend.processing.theaters import theater_geometries

router = APIRouter(prefix="/api/pressure", tags=["pressure"])

SEVERITY_WEIGHTS = {
    SeverityLevel.LOW: 1,
    SeverityLevel.MEDIUM: 2,
    SeverityLevel.HIGH: 4,
    SeverityLevel.CRITICAL: 8,
}

ESCALATION_RATIO = 1.5
# One single-Source critical Event, two single-Source high Events, or one high Event with 2 Sources
ESCALATION_FLOOR = 1.6


def is_escalating(current: float, previous: float) -> bool:
    """Pressure rose to at least ESCALATION_RATIO × the window before and by at least ESCALATION_FLOOR.

    From 0, only the floor applies.
    """
    # Rounded so sums like 4.8 - 3.2 = 1.5999... still meet the threshold they meet on paper
    return (
        round(current - ESCALATION_RATIO * previous, 6) >= 0
        and round(current - previous, 6) >= ESCALATION_FLOOR
    )


async def theater_pressure(session: AsyncSession, window_hours: int) -> dict[str, tuple[float, float]]:
    """(Pressure now, Pressure in the window before) for each Theater with Events in either window."""
    now = datetime.utcnow()
    window = timedelta(hours=window_hours)
    weight = case(*((Event.severity == level, w) for level, w in SEVERITY_WEIGHTS.items()))
    score = weight * func.coalesce(Event.confidence_score, 0.0)
    current = func.coalesce(func.sum(score).filter(Event.created_at >= now - window), 0.0)
    previous = func.coalesce(func.sum(score).filter(Event.created_at < now - window), 0.0)
    result = await session.execute(
        select(Event.theater, current, previous)
        .where(Event.theater.isnot(None), Event.created_at >= now - 2 * window, Event.created_at <= now)
        .group_by(Event.theater)
    )
    return {theater: (in_window, in_window_before) for theater, in_window, in_window_before in result}


@router.get("")
async def get_pressure(
    db: AsyncSession = Depends(get_db),
    window_hours: int = Query(24, gt=0, description="Length of the window ending now, in hours"),
):
    """Every Theater's polygon with its Pressure now and in the window before, as GeoJSON."""
    pressure = await theater_pressure(db, window_hours)
    features = []
    for name, geometry in theater_geometries():
        current, previous = (round(p, 3) for p in pressure.get(name, (0.0, 0.0)))
        features.append({
            "type": "Feature",
            "geometry": geometry,
            "properties": {
                "name": name,
                "pressure": current,
                "previous_pressure": previous,
                "escalating": is_escalating(current, previous),
            },
        })
    return {"type": "FeatureCollection", "features": features}
