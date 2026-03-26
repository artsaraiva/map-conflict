from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
from typing import Optional

from backend.core.database import get_db
from backend.models.event import Event, Article
from backend.api.schemas import EventResponse, EventListResponse, EventMapPoint

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("/", response_model=EventListResponse)
async def get_events(
    db: AsyncSession = Depends(get_db),
    min_lat: Optional[float] = Query(
        None, description="Minimum latitude (bounding box)"
    ),
    max_lat: Optional[float] = Query(
        None, description="Maximum latitude (bounding box)"
    ),
    min_lng: Optional[float] = Query(
        None, description="Minimum longitude (bounding box)"
    ),
    max_lng: Optional[float] = Query(
        None, description="Maximum longitude (bounding box)"
    ),
    event_type: Optional[str] = Query(
        None, description="Filter by event type (comma-separated for multiple)"
    ),
    severity: Optional[str] = Query(
        None, description="Filter by severity (comma-separated for multiple)"
    ),
    since_hours: int = Query(72, description="Show events from last N hours"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """Get events, optionally filtered by bounding box, type, and severity."""
    since = datetime.utcnow() - timedelta(hours=since_hours)
    query = select(Event).where(Event.created_at >= since)

    # Bounding box filter
    if all(v is not None for v in [min_lat, max_lat, min_lng, max_lng]):
        query = query.where(
            Event.latitude >= min_lat,
            Event.latitude <= max_lat,
            Event.longitude >= min_lng,
            Event.longitude <= max_lng,
        )

    if event_type:
        types = [t.strip() for t in event_type.split(",") if t.strip()]
        if len(types) == 1:
            query = query.where(Event.event_type == types[0])
        elif types:
            query = query.where(Event.event_type.in_(types))

    if severity:
        severities = [s.strip() for s in severity.split(",") if s.strip()]
        if len(severities) == 1:
            query = query.where(Event.severity == severities[0])
        elif severities:
            query = query.where(Event.severity.in_(severities))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get paginated results
    query = query.order_by(Event.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    events = result.scalars().all()

    return EventListResponse(
        events=[EventResponse.model_validate(e) for e in events],
        total=total,
    )


@router.get("/map-points", response_model=list[EventMapPoint])
async def get_map_points(
    db: AsyncSession = Depends(get_db),
    event_type: Optional[str] = Query(
        None, description="Filter by event type (comma-separated for multiple)"
    ),
    severity: Optional[str] = Query(
        None, description="Filter by severity (comma-separated for multiple)"
    ),
    since_hours: int = Query(72, description="Show events from last N hours"),
):
    """Get lightweight event data optimized for map rendering."""
    since = datetime.utcnow() - timedelta(hours=since_hours)
    query = select(Event).where(Event.created_at >= since)

    if event_type:
        types = [t.strip() for t in event_type.split(",") if t.strip()]
        if len(types) == 1:
            query = query.where(Event.event_type == types[0])
        elif types:
            query = query.where(Event.event_type.in_(types))

    if severity:
        severities = [s.strip() for s in severity.split(",") if s.strip()]
        if len(severities) == 1:
            query = query.where(Event.severity == severities[0])
        elif severities:
            query = query.where(Event.severity.in_(severities))

    query = query.order_by(Event.created_at.desc())

    result = await db.execute(query)
    events = result.scalars().all()

    return [
        EventMapPoint(
            id=e.id,
            title=e.title,
            event_type=e.event_type.value if e.event_type else "other",
            severity=e.severity.value if e.severity else "medium",
            latitude=e.latitude,
            longitude=e.longitude,
            location_name=e.location_name,
            article_count=len(e.articles) if e.articles else 0,
            image_url=next(
                (a.image_url for a in (e.articles or []) if a.image_url), None
            ),
            sources=list(
                dict.fromkeys(a.source for a in (e.articles or []) if a.source)
            ),
            created_at=e.created_at,
        )
        for e in events
    ]


@router.get("/{event_id}", response_model=EventResponse)
async def get_event(event_id: int, db: AsyncSession = Depends(get_db)):
    """Get a single event with its linked articles."""
    result = await db.execute(select(Event).where(Event.id == event_id))
    event = result.scalar_one_or_none()

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return EventResponse.model_validate(event)
