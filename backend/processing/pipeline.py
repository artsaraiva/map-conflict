"""
Main processing pipeline: scrape -> classify -> geocode -> store.
Multi-source ingestion: Telegram + RSS feeds.
"""

import asyncio
import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import selectinload

from backend.core.config import get_settings
from backend.models.event import Event, Article, EventRelationship, EventType, SeverityLevel
from backend.scraping.rss_scraper import ScrapedArticle, scrape_all_feeds
from backend.processing.nlp import classify_article, text_similarity
from backend.processing.geocoder import geocode_location

logger = logging.getLogger(__name__)

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


async def _get_session() -> AsyncSession:
    """Create a standalone async session for pipeline use."""
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    return session_factory()


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


def _strip_tz(dt: datetime | None) -> datetime | None:
    """Strip timezone info for naive TIMESTAMP columns."""
    if dt is None:
        return None
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


async def process_article(session: AsyncSession, scraped: ScrapedArticle) -> bool:
    """
    Process a single scraped article through the full pipeline.
    Returns True if an event was created/updated.
    """
    # Normalize published_at to naive UTC
    scraped.published_at = _strip_tz(scraped.published_at)

    # Skip if already processed
    if await _article_exists(session, scraped.url):
        return False

    # Classify the article
    analysis = await classify_article(scraped.title, scraped.description)
    if analysis is None or not analysis.is_geopolitical:
        # Still store the article for dedup purposes, but don't create an event
        article = Article(
            url=scraped.url,
            title=scraped.title,
            source=scraped.source,
            summary=scraped.description[:500] if scraped.description else None,
            image_url=scraped.image_url,
            video_url=scraped.video_url,
            published_at=scraped.published_at,
        )
        session.add(article)
        await session.commit()
        return False

    # Geocode the primary location
    primary_location = analysis.locations[0] if analysis.locations else None
    if not primary_location:
        logger.debug(f"No location found for: {scraped.title}")
        return False

    geo = await geocode_location(primary_location)
    if not geo:
        logger.debug(f"Could not geocode: {primary_location}")
        return False

    # Map string types to enums
    try:
        event_type = EventType(analysis.event_type)
    except ValueError:
        event_type = EventType.OTHER

    try:
        severity = SeverityLevel(analysis.severity)
    except ValueError:
        severity = SeverityLevel.MEDIUM

    # Check for existing similar event (fuzzy cross-channel deduplication)
    article_text = scraped.description or scraped.title
    existing_event = await _find_similar_event(session, article_text, event_type.value)

    if existing_event:
        # Add article to existing event
        article = Article(
            url=scraped.url,
            title=scraped.title,
            source=scraped.source,
            summary=analysis.summary or scraped.description[:500],
            image_url=scraped.image_url,
            video_url=scraped.video_url,
            published_at=scraped.published_at,
            event_id=existing_event.id,
        )
        session.add(article)

        # Update event severity if this article suggests higher severity
        severity_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        if severity_order.get(analysis.severity, 0) > severity_order.get(
            existing_event.severity.value if existing_event.severity else "medium", 0
        ):
            existing_event.severity = severity

        # Refresh intelligence fields
        new_source_count = len(
            {a.source for a in existing_event.articles if a.source} | {scraped.source}
        )
        existing_event.source_count = new_source_count
        existing_event.confidence_score = _compute_confidence(new_source_count)
        existing_event.updated_at = datetime.utcnow()
        await session.commit()
        logger.info(f"Added article to existing event: {existing_event.title}")
        return True

    # Create new event
    event = Event(
        title=scraped.title,
        summary=analysis.summary or scraped.description[:500],
        event_type=event_type,
        severity=severity,
        location_name=geo.name,
        latitude=geo.latitude,
        longitude=geo.longitude,
        countries=",".join(analysis.countries) if analysis.countries else None,
        theater=_derive_theater(geo.latitude, geo.longitude),
        source_count=1,
        confidence_score=_compute_confidence(1),
    )
    session.add(event)
    await session.flush()  # Get the event ID

    # Create article linked to event
    article = Article(
        url=scraped.url,
        title=scraped.title,
        source=scraped.source,
        summary=analysis.summary or scraped.description[:500],
        image_url=scraped.image_url,
        video_url=scraped.video_url,
        published_at=scraped.published_at,
        event_id=event.id,
    )
    session.add(article)

    # Build semantic relationships with other recent events
    await _link_related_events(session, event, article_text)

    await session.commit()

    logger.info(
        f"Created new event: {event.title} at {geo.name} ({geo.latitude}, {geo.longitude})"
    )
    return True


async def run_telegram_pipeline():
    """Run the Telegram scrape -> process -> store pipeline."""
    from backend.scraping.telegram_scraper import scrape_telegram_channels

    logger.info("Starting Telegram pipeline run...")

    articles = await scrape_telegram_channels()
    if not articles:
        logger.info("Telegram pipeline: no articles to process.")
        return 0

    logger.info(f"Telegram scraped {len(articles)} messages, processing...")

    session = await _get_session()
    events_created = 0

    try:
        for scraped in articles:
            try:
                if await process_article(session, scraped):
                    events_created += 1
            except Exception as e:
                logger.error(
                    f"Error processing Telegram message '{scraped.title}': {e}"
                )
                await session.rollback()
                continue
    finally:
        await session.close()

    logger.info(f"Telegram pipeline complete. Events created/updated: {events_created}")
    return events_created


async def run_rss_pipeline():
    """Run the RSS scrape -> process -> store pipeline."""
    settings = get_settings()
    max_per_feed = settings.max_articles_per_feed

    logger.info(f"Starting RSS pipeline run (max {max_per_feed}/feed)...")

    articles = await scrape_all_feeds(max_articles_per_feed=max_per_feed)
    if not articles:
        logger.info("RSS pipeline: no articles to process.")
        return 0

    logger.info(f"RSS scraped {len(articles)} articles, processing...")

    session = await _get_session()
    events_created = 0

    try:
        for scraped in articles:
            try:
                if await process_article(session, scraped):
                    events_created += 1
            except Exception as e:
                logger.error(f"Error processing RSS article '{scraped.title}': {e}")
                await session.rollback()
                continue
    finally:
        await session.close()

    logger.info(f"RSS pipeline complete. Events created/updated: {events_created}")
    return events_created


async def run_x_pipeline():
    """Run the X (Twitter) scrape -> process -> store pipeline."""
    from backend.scraping.x_scraper import scrape_x_accounts

    logger.info("Starting X pipeline run...")

    articles = await scrape_x_accounts()
    if not articles:
        logger.info("X pipeline: no articles to process (token missing or no results).")
        return 0

    logger.info(f"X scraped {len(articles)} tweets, processing...")

    session = await _get_session()
    events_created = 0

    try:
        for scraped in articles:
            try:
                if await process_article(session, scraped):
                    events_created += 1
            except Exception as e:
                logger.error(f"Error processing X tweet '{scraped.title}': {e}")
                await session.rollback()
                continue
    finally:
        await session.close()

    logger.info(f"X pipeline complete. Events created/updated: {events_created}")
    return events_created


async def run_gdelt_pipeline():
    """Run the GDELT Doc API scrape -> process -> store pipeline."""
    from backend.scraping.gdelt_scraper import scrape_gdelt

    logger.info("Starting GDELT pipeline run...")

    articles = await scrape_gdelt()
    if not articles:
        logger.info("GDELT pipeline: no articles returned.")
        return 0

    logger.info(f"GDELT scraped {len(articles)} articles, processing...")

    session = await _get_session()
    events_created = 0

    try:
        for scraped in articles:
            try:
                if await process_article(session, scraped):
                    events_created += 1
            except Exception as e:
                logger.error(f"Error processing GDELT article '{scraped.title}': {e}")
                await session.rollback()
                continue
    finally:
        await session.close()

    logger.info(f"GDELT pipeline complete. Events created/updated: {events_created}")
    return events_created


async def run_all_sources_pipeline():
    """
    Run all ingestion sources concurrently: Telegram + RSS + X + GDELT.

    Each source is independent — if one fails, the others still complete.
    Returns a dict with per-source event counts.
    """
    logger.info("Starting multi-source pipeline run...")

    results = await asyncio.gather(
        run_telegram_pipeline(),
        run_rss_pipeline(),
        run_x_pipeline(),
        run_gdelt_pipeline(),
        return_exceptions=True,
    )

    telegram_count = results[0] if isinstance(results[0], int) else 0
    rss_count = results[1] if isinstance(results[1], int) else 0
    x_count = results[2] if isinstance(results[2], int) else 0
    gdelt_count = results[3] if isinstance(results[3], int) else 0

    if isinstance(results[0], BaseException):
        logger.error(f"Telegram pipeline failed: {results[0]}")
    if isinstance(results[1], BaseException):
        logger.error(f"RSS pipeline failed: {results[1]}")
    if isinstance(results[2], BaseException):
        logger.error(f"X pipeline failed: {results[2]}")
    if isinstance(results[3], BaseException):
        logger.error(f"GDELT pipeline failed: {results[3]}")

    total = telegram_count + rss_count + x_count + gdelt_count
    logger.info(
        f"Multi-source pipeline complete. "
        f"Telegram: {telegram_count}, RSS: {rss_count}, X: {x_count}, "
        f"GDELT: {gdelt_count}, Total: {total}"
    )

    return {
        "telegram": telegram_count,
        "rss": rss_count,
        "x": x_count,
        "gdelt": gdelt_count,
        "total": total,
    }
