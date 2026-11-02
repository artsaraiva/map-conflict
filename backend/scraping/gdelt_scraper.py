"""
GDELT 2.0 Doc API scraper for geopolitical news events.

Free, no authentication required.
https://blog.gdeltproject.org/gdelt-doc-2-0-api-debuts/

The GDELT Doc API monitors global news in real-time. We use the `artlist`
mode to retrieve recent articles matching geopolitical query terms.
"""

import asyncio
import httpx
from datetime import datetime, timezone
from typing import Optional
import logging

from backend.scraping.rss_scraper import ScrapedArticle

logger = logging.getLogger(__name__)

GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"

# Curated queries covering the main geopolitical domains tracked by the product.
# Each runs against the last 24 hours of GDELT's global news index.
GDELT_QUERIES = [
    {
        "query": "airstrike military attack offensive conflict war",
        "source": "gdelt",
        "max": 50,
    },
    {
        "query": "protest demonstration civil unrest riot",
        "source": "gdelt",
        "max": 30,
    },
    {
        "query": "sanctions diplomacy ceasefire peace agreement treaty",
        "source": "gdelt",
        "max": 30,
    },
    {
        "query": "Ukraine Russia front line offensive Kharkiv Zaporizhzhia",
        "source": "gdelt",
        "max": 50,
    },
    {
        "query": "Gaza Hamas IDF Palestine Rafah ceasefire",
        "source": "gdelt",
        "max": 40,
    },
    {
        "query": "Taiwan China military naval strait exercise",
        "source": "gdelt",
        "max": 30,
    },
    {
        "query": "Red Sea Houthi shipping tanker attack",
        "source": "gdelt",
        "max": 30,
    },
    {
        "query": "nuclear missile ballistic test North Korea Iran",
        "source": "gdelt",
        "max": 20,
    },
]


def _parse_gdelt_date(seendate: str) -> Optional[datetime]:
    """Parse GDELT's compact YYYYMMDDTHHMMSSZ timestamp format."""
    if not seendate:
        return None
    try:
        return datetime.strptime(seendate, "%Y%m%dT%H%M%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        return None


async def _scrape_gdelt_query(
    query_config: dict, client: httpx.AsyncClient
) -> list[ScrapedArticle]:
    """Fetch articles from GDELT Doc API for a single query term."""
    params = {
        "query": query_config["query"],
        "mode": "artlist",
        "maxrecords": str(query_config["max"]),
        "format": "json",
        "timespan": "1d",  # last 24 hours
    }
    try:
        resp = await client.get(GDELT_DOC_API, params=params, timeout=30.0)
        resp.raise_for_status()
        data = resp.json()
        articles_raw = data.get("articles") or []
    except Exception as exc:
        logger.warning(
            "GDELT query failed (query=%r): %s", query_config["query"][:60], exc
        )
        return []

    articles: list[ScrapedArticle] = []
    for raw in articles_raw:
        url = (raw.get("url") or "").strip()
        title = (raw.get("title") or "").strip()
        if not url or not title:
            continue
        # Only English-language articles for NLP compatibility
        if (raw.get("language") or "English") != "English":
            continue
        articles.append(
            ScrapedArticle(
                url=url,
                title=title,
                source=query_config["source"],
                # GDELT artlist mode doesn't include article body excerpts —
                # use the title as the description so the NLP pipeline has
                # something to work with.
                description=title,
                published_at=_parse_gdelt_date(raw.get("seendate") or ""),
            )
        )

    return articles


async def scrape_gdelt() -> list[ScrapedArticle]:
    """
    Scrape all GDELT queries concurrently and return deduplicated articles.

    Returns an empty list on total failure so the pipeline degrades gracefully.
    """
    async with httpx.AsyncClient(follow_redirects=True) as client:
        batches = await asyncio.gather(
            *[_scrape_gdelt_query(q, client) for q in GDELT_QUERIES],
            return_exceptions=True,
        )

    seen_urls: set[str] = set()
    articles: list[ScrapedArticle] = []

    for batch in batches:
        if isinstance(batch, BaseException):
            logger.warning("GDELT batch error: %s", batch)
            continue
        for article in batch:
            if article.url not in seen_urls:
                seen_urls.add(article.url)
                articles.append(article)

    logger.info(
        "GDELT: scraped %d unique articles across %d queries",
        len(articles),
        len(GDELT_QUERIES),
    )
    return articles
