"""
Event intake: turns Reports into Events.

`ingest` takes a batch of Reports and returns one Outcome per Report, in input
order. Each Report is processed in its own transaction: the already-seen check,
classification, geocoding, matching to a recent Event (or creating one),
Severity, Corroboration and Confidence, Theater, and Links. Classification and
geocoding run in parallel across Feeds; matching onward runs under an advisory
lock, so concurrent Feeds never create two Events for one occurrence.
"""

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from backend.models.event import (
    Article,
    Event,
    EventRelationship,
    EventType,
    SeverityLevel,
)
from backend.processing.geocoder import GeocodedLocation
from backend.processing.nlp import ArticleAnalysis, text_similarity
from backend.scraping.sources import source_key

logger = logging.getLogger(__name__)


@dataclass
class Report:
    """
    A single Report: published by one Source, received through one Feed.

    Adapters fill the content fields, and `source` when the Feed names the Source
    (a raw value such as GDELT's `domain`). `published_at` must be timezone-aware,
    or naive and already UTC. `run_feed` stamps `feed`; `ingest` turns `source`,
    or the URL when it is empty, into the canonical Source key.
    """

    url: str
    title: str
    description: str = ""
    published_at: datetime | None = None
    image_url: str | None = None
    video_url: str | None = None
    source: str = ""
    feed: str = ""


@dataclass
class Outcome:
    """What happened to one Report. `event` is set for created/corroborated, `error` for failed."""

    kind: Literal["created", "corroborated", "already_seen", "not_geopolitical", "unplaced", "failed"]
    event: Event | None = None
    error: Exception | None = None


Classify = Callable[[str, str], Awaitable[ArticleAnalysis | None]]
Geocode = Callable[[str], Awaitable[GeocodedLocation | None]]


async def ingest(
    reports: list[Report],
    classify: Classify,
    geocode: Geocode,
    session_factory: async_sessionmaker[AsyncSession],
) -> list[Outcome]:
    """Process each Report in its own transaction; a failing Report gives `failed` and the batch goes on."""
    outcomes = []
    for report in reports:
        try:
            async with session_factory() as session, session.begin():
                outcomes.append(await _ingest_one(session, report, classify, geocode))
        except Exception as e:
            logger.error(f"Error processing Report '{report.title}': {e}")
            outcomes.append(Outcome("failed", error=e))
    return outcomes


# ── Theater bounding boxes (checked in order; first match wins) ───────────────
# Each entry: (name, lat_min, lat_max, lng_min, lng_max)
_THEATER_REGIONS = [
    ("Eastern Europe", 44.0, 71.0, 14.0, 50.0),
    ("Middle East", 12.0, 42.0, 25.0, 63.0),
    ("East Asia", 10.0, 55.0, 100.0, 145.0),
    ("South Asia", 5.0, 38.0, 60.0, 100.0),
    ("Central Asia", 35.0, 57.0, 50.0, 90.0),
    ("North Africa", 15.0, 38.0, -18.0, 42.0),
    ("Sub-Saharan Africa", -35.0, 15.0, -20.0, 52.0),
    ("Americas", -60.0, 72.0, -170.0, -30.0),
    ("Western Europe", 35.0, 72.0, -10.0, 30.0),
    ("Southeast Asia", -10.0, 28.0, 95.0, 141.0),
    ("Pacific", -50.0, 50.0, 141.0, 180.0),
]


def _derive_theater(lat: float, lng: float) -> str:
    """Assign a geopolitical theater label from a coordinate pair."""
    for name, lat_min, lat_max, lng_min, lng_max in _THEATER_REGIONS:
        if lat_min <= lat <= lat_max and lng_min <= lng <= lng_max:
            return name
    return "Other"


async def _refresh_corroboration(session: AsyncSession, event: Event) -> None:
    """Corroboration is the number of distinct Sources across the Event's Reports; Confidence follows it."""
    await session.flush()  # the count must see the Report just stored
    event.source_count = await session.scalar(
        select(func.count(distinct(Article.source))).where(Article.event_id == event.id)
    )
    event.confidence_score = _compute_confidence(event.source_count)


def _compute_confidence(source_count: int) -> float:
    """
    Simple confidence score (0.0–1.0) based on the number of distinct sources
    corroborating an event.  Single-source events are low confidence; five or
    more independent sources yield full confidence.
    """
    return round(min(source_count / 5.0, 1.0), 2)


async def _link_related_events(
    session: AsyncSession,
    new_event: Event,
    article_text: str,
    threshold: float = 0.35,
) -> None:
    """
    Compare a newly created event against recent events and insert bidirectional
    EventRelationship rows for any pair with similarity >= threshold.
    Skips pairs that are already linked.
    """
    cutoff = datetime.utcnow() - timedelta(hours=DEDUP_WINDOW_HOURS * 4)  # wider window for relations

    result = await session.execute(
        select(Event)
        .options(selectinload(Event.articles))
        .where(Event.created_at >= cutoff)
        .where(Event.id != new_event.id)
    )
    candidates = result.scalars().all()

    for candidate in candidates:
        for existing_article in candidate.articles:
            existing_text = existing_article.summary or existing_article.title or ""
            score = text_similarity(article_text, existing_text)
            if score < threshold:
                continue

            # Avoid duplicate constraint — check both directions
            existing = await session.execute(
                select(EventRelationship).where(
                    EventRelationship.source_event_id == new_event.id,
                    EventRelationship.target_event_id == candidate.id,
                )
            )
            if existing.scalar_one_or_none() is not None:
                break

            session.add(EventRelationship(
                source_event_id=new_event.id,
                target_event_id=candidate.id,
                relation_type="similar",
                similarity_score=round(score, 3),
                created_at=datetime.utcnow(),
            ))
            session.add(EventRelationship(
                source_event_id=candidate.id,
                target_event_id=new_event.id,
                relation_type="similar",
                similarity_score=round(score, 3),
                created_at=datetime.utcnow(),
            ))
            break  # one match per candidate is enough


# ── Similarity thresholds for cross-channel deduplication ────────────────────
# If event types match: lower threshold (likely same story from different angle)
SIMILARITY_THRESHOLD_SAME_TYPE = 0.5
# If event types differ: higher bar (must be clearly the same story)
SIMILARITY_THRESHOLD_ANY_TYPE = 0.7
# Only consider events created in the last N hours for merging
DEDUP_WINDOW_HOURS = 6

# Advisory lock key that serializes match-or-create across concurrent Feeds
_INTAKE_LOCK_KEY = 1801


async def _article_exists(session: AsyncSession, url: str) -> bool:
    """Check if an article with this URL already exists."""
    result = await session.execute(select(Article).where(Article.url == url).limit(1))
    return result.scalar_one_or_none() is not None


async def _find_similar_event(
    session: AsyncSession, article_text: str, event_type: str
) -> Event | None:
    """
    Find a recent event whose articles are textually similar to the new article.

    Uses Jaccard word-overlap similarity across all articles belonging to each
    recent event.  Two thresholds:
      - >0.5 if the event type matches (same kind of story)
      - >0.7 regardless of event type (clearly the same story)

    Returns the best-matching event, or None.
    """
    cutoff = datetime.utcnow() - timedelta(hours=DEDUP_WINDOW_HOURS)

    result = await session.execute(
        select(Event)
        .options(selectinload(Event.articles))
        .where(Event.created_at >= cutoff)
    )
    recent_events = result.scalars().all()

    best_event: Event | None = None
    best_score: float = 0.0

    for event in recent_events:
        # Compare new article text against each article in this event
        for existing_article in event.articles:
            existing_text = existing_article.summary or existing_article.title or ""
            score = text_similarity(article_text, existing_text)

            # Determine threshold based on type match
            if event.event_type and event.event_type.value == event_type:
                threshold = SIMILARITY_THRESHOLD_SAME_TYPE
            else:
                threshold = SIMILARITY_THRESHOLD_ANY_TYPE

            if score >= threshold and score > best_score:
                best_score = score
                best_event = event

    if best_event:
        logger.info(
            f"Fuzzy dedup match (score={best_score:.2f}): "
            f"merging into event '{best_event.title}'"
        )

    return best_event


def _to_naive_utc(dt: datetime | None) -> datetime | None:
    """Convert to UTC, then drop tzinfo for naive TIMESTAMP columns. Naive input is taken as UTC."""
    if dt is None or dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def _store_report(
    session: AsyncSession, report: Report, summary: str | None, event_id: int | None = None
) -> None:
    """Add the Report's row; `event_id` is None when it belongs to no Event."""
    session.add(Article(
        url=report.url,
        title=report.title,
        source=report.source,
        feed=report.feed,
        summary=summary,
        image_url=report.image_url,
        video_url=report.video_url,
        published_at=report.published_at,
        event_id=event_id,
    ))


async def _ingest_one(
    session: AsyncSession, report: Report, classify: Classify, geocode: Geocode
) -> Outcome:
    """Process one Report inside the caller's transaction; the caller commits."""
    report.published_at = _to_naive_utc(report.published_at)
    report.source = source_key(report.source or report.url)

    # Skip if already processed
    if await _article_exists(session, report.url):
        return Outcome("already_seen")

    # Classify the article
    analysis = await classify(report.title, report.description)
    if analysis is None or not analysis.is_geopolitical:
        # Still store the article for dedup purposes, but don't create an event
        _store_report(session, report, report.description[:500] if report.description else None)
        return Outcome("not_geopolitical")

    # Unplaced Reports are stored with no Event, so they are never classified again
    summary = analysis.summary or report.description[:500]
    primary_location = analysis.locations[0] if analysis.locations else None
    if not primary_location:
        logger.debug(f"No location found for: {report.title}")
        _store_report(session, report, summary)
        return Outcome("unplaced")

    geo = await geocode(primary_location)
    if not geo:
        logger.debug(f"Could not geocode: {primary_location}")
        _store_report(session, report, summary)
        return Outcome("unplaced")

    # Map string types to enums
    try:
        event_type = EventType(analysis.event_type)
    except ValueError:
        event_type = EventType.OTHER

    try:
        severity = SeverityLevel(analysis.severity)
    except ValueError:
        severity = SeverityLevel.MEDIUM

    # Matching to an Event, or creating one, and the write that follows run one Report at a
    # time across all Feeds; the lock lasts until the caller's transaction ends. Needs READ
    # COMMITTED, so the match query after the lock sees the Event another Feed just committed.
    # ponytail: one global lock key, finer-grained keys (e.g. per Theater) if throughput matters
    await session.execute(select(func.pg_advisory_xact_lock(_INTAKE_LOCK_KEY)))

    # Check for existing similar event (fuzzy cross-channel deduplication)
    article_text = report.description or report.title
    existing_event = await _find_similar_event(session, article_text, event_type.value)

    if existing_event:
        # Add article to existing event
        _store_report(session, report, summary, existing_event.id)

        # Update event severity if this article suggests higher severity
        severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        if severity_order.get(analysis.severity, 0) > severity_order.get(
            existing_event.severity.value if existing_event.severity else "medium", 0
        ):
            existing_event.severity = severity

        await _refresh_corroboration(session, existing_event)
        existing_event.updated_at = datetime.utcnow()
        logger.info(f"Added Report to existing Event: {existing_event.title}")
        return Outcome("corroborated", event=existing_event)

    # Create new event
    event = Event(
        title=report.title,
        summary=summary,
        event_type=event_type,
        severity=severity,
        location_name=geo.name,
        latitude=geo.latitude,
        longitude=geo.longitude,
        countries=",".join(analysis.countries) if analysis.countries else None,
        theater=_derive_theater(geo.latitude, geo.longitude),
    )
    session.add(event)
    await session.flush()  # Get the event ID

    # Create article linked to event
    _store_report(session, report, summary, event.id)
    await _refresh_corroboration(session, event)

    # Build semantic relationships with other recent events
    await _link_related_events(session, event, article_text)

    logger.info(
        f"Created new Event: {event.title} at {geo.name} ({geo.latitude}, {geo.longitude})"
    )
    return Outcome("created", event=event)
