from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import ARRAY, String, case, func, or_, select, type_coerce
from sqlalchemy.dialects.postgresql import aggregate_order_by, array
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from typing import Optional

from backend.core.database import get_db
from backend.models.event import Event, Article, Link
from backend.api.schemas import EventResponse, EventMapPoint, LinkResponse

router = APIRouter(prefix="/api/events", tags=["events"])


async def map_points(
    session: AsyncSession,
    since_hours: int,
    bbox: tuple[float, float, float, float] | None = None,
    event_types: tuple[str, ...] = (),
    severities: tuple[str, ...] = (),
    theaters: tuple[str, ...] = (),
) -> list[EventMapPoint]:
    """Events created in the last `since_hours`, newest first.

    `bbox` is `(min_lat, max_lat, min_lng, max_lng)`. An empty filter tuple matches everything.
    """
    since = datetime.utcnow() - timedelta(hours=since_hours)
    report_count = func.count(Article.id).label("article_count")
    sources = func.array_agg(
        aggregate_order_by(Article.source.distinct(), Article.source)
    ).filter(Article.source.isnot(None))
    images = func.array_agg(aggregate_order_by(Article.image_url, Article.id)).filter(
        Article.image_url.isnot(None)
    )
    query = (
        select(
            Event.id,
            Event.title,
            Event.event_type,
            Event.severity,
            Event.latitude,
            Event.longitude,
            Event.location_name,
            Event.created_at,
            Event.confidence_score,
            Event.source_count,
            Event.theater,
            report_count,
            func.coalesce(sources, array([], type_=String)).label("sources"),
            type_coerce(images, ARRAY(String))[1].label("image_url"),
        )
        .outerjoin(Article, Article.event_id == Event.id)
        .where(Event.created_at >= since)
        .group_by(Event.id)
        .order_by(Event.created_at.desc())
    )
    if bbox is not None:
        min_lat, max_lat, min_lng, max_lng = bbox
        query = query.where(
            Event.latitude.between(min_lat, max_lat),
            Event.longitude.between(min_lng, max_lng),
        )
    for column, values in (
        (Event.event_type, event_types),
        (Event.severity, severities),
        (Event.theater, theaters),
    ):
        if values:
            query = query.where(column.in_(values))
    result = await session.execute(query)
    return [EventMapPoint.model_validate(row, from_attributes=True) for row in result]


def _csv(s: Optional[str]) -> tuple[str, ...]:
    return tuple(v.strip() for v in (s or "").split(",") if v.strip())


@router.get("/map-points", response_model=list[EventMapPoint])
async def get_map_points(
    db: AsyncSession = Depends(get_db),
    min_lat: Optional[float] = Query(None, description="Bounding box south latitude"),
    max_lat: Optional[float] = Query(None, description="Bounding box north latitude"),
    min_lng: Optional[float] = Query(None, description="Bounding box west longitude"),
    max_lng: Optional[float] = Query(None, description="Bounding box east longitude"),
    event_type: Optional[str] = Query(
        None, description="Filter by event type (comma-separated for multiple)"
    ),
    severity: Optional[str] = Query(
        None, description="Filter by severity (comma-separated for multiple)"
    ),
    theater: Optional[str] = Query(
        None, description="Filter by theater name (comma-separated for multiple)"
    ),
    since_hours: int = Query(72, description="Show events from last N hours"),
):
    """Get lightweight event data optimized for map rendering."""
    corners = (min_lat, max_lat, min_lng, max_lng)
    return await map_points(
        db,
        since_hours,
        bbox=None if None in corners else corners,
        event_types=_csv(event_type),
        severities=_csv(severity),
        theaters=_csv(theater),
    )


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single event with its linked articles."""
    result = await db.execute(
        select(Event).options(selectinload(Event.articles)).where(Event.id == event_id)
    )
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return EventResponse.model_validate(event)


@router.get("/{event_id}/links", response_model=list[LinkResponse])
async def get_event_links(event_id: int, db: AsyncSession = Depends(get_db)):
    """Every Link touching the Event, newest linked Event first."""
    other_id = case((Link.from_event_id == event_id, Link.to_event_id), else_=Link.from_event_id)
    result = await db.execute(
        select(Link, Event)
        .join(Event, Event.id == other_id)
        .where(or_(Link.from_event_id == event_id, Link.to_event_id == event_id))
        .order_by(Event.created_at.desc())
    )

    return [
        LinkResponse(
            id=event.id,
            title=event.title,
            event_type=event.event_type,
            severity=event.severity,
            location_name=event.location_name,
            latitude=event.latitude,
            longitude=event.longitude,
            theater=event.theater,
            confidence_score=event.confidence_score,
            created_at=event.created_at,
            link_type=link.link_type,
            direction="outgoing" if link.from_event_id == event_id else "incoming",
        )
        for link, event in result.all()
    ]
