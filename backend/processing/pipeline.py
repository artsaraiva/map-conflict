"""
Main processing pipeline: scrape -> Event intake.
Every Feed adapter returns Reports; run_feed hands them to `ingest`.
"""

import asyncio
import logging
from collections import Counter

from backend.core.config import get_settings
from backend.core.database import async_session
from backend.processing.geocoder import geocode_location
from backend.processing.intake import ingest
from backend.processing.nlp import classify_article
from backend.scraping.gdelt_scraper import scrape_gdelt
from backend.scraping.rss_scraper import scrape_all_feeds
from backend.scraping.sources import source_key
from backend.scraping.telegram_scraper import scrape_telegram_channels
from backend.scraping.x_scraper import scrape_x_accounts

logger = logging.getLogger(__name__)

FEEDS = {
    "telegram": scrape_telegram_channels,
    "rss": lambda: scrape_all_feeds(get_settings().max_articles_per_feed),
    "x": scrape_x_accounts,
    "gdelt": scrape_gdelt,
}


async def run_feed(name: str) -> int:
    """Fetch one Feed's Reports and ingest them. Returns Events created or corroborated."""
    reports = await FEEDS[name]()
    logger.info(f"{name}: fetched {len(reports)} Reports")
    if not reports:
        return 0

    for report in reports:
        report.feed = name
        report.source = report.source or source_key(report.url)
    outcomes = await ingest(reports, classify_article, geocode_location, async_session)

    counts = Counter(o.kind for o in outcomes)
    logger.info(f"{name}: Report outcomes: {dict(counts)}")
    return counts["created"] + counts["corroborated"]


async def run_all_feeds() -> dict[str, int]:
    """Run every Feed concurrently; one failing Feed does not stop the others."""
    results = await asyncio.gather(*(run_feed(n) for n in FEEDS), return_exceptions=True)
    counts = {}
    for name, result in zip(FEEDS, results):
        if isinstance(result, BaseException):
            logger.error(f"{name} Feed failed: {result}")
            result = 0
        counts[name] = result
    counts["total"] = sum(counts.values())
    logger.info(f"All Feeds complete: {counts}")
    return counts
