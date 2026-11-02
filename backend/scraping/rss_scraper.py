"""
RSS Feed scraper for geopolitical news sources.
"""

import asyncio
import re
import feedparser
import httpx
from datetime import datetime
from dateutil import parser as dateparser
from typing import Optional
import logging

from backend.processing.intake import Report

logger = logging.getLogger(__name__)

# Curated list of geopolitics-focused RSS feeds
RSS_FEEDS = [
    {
        "name": "BBC World",
        "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
    },
    {
        "name": "Al Jazeera",
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
    },
    {
        "name": "AP News",
        "url": "https://feedx.net/rss/ap.xml",
    },
    {
        "name": "CNN World",
        "url": "http://rss.cnn.com/rss/edition_world.rss",
    },
    {
        "name": "The Guardian World",
        "url": "https://www.theguardian.com/world/rss",
    },
    {
        "name": "NPR World",
        "url": "https://feeds.npr.org/1004/rss.xml",
    },
    {
        "name": "France24",
        "url": "https://www.france24.com/en/rss",
    },
    {
        "name": "DW World",
        "url": "https://rss.dw.com/rdf/rss-en-world",
    },
]


def parse_date(date_str: str) -> Optional[datetime]:
    """Try to parse various date formats from RSS feeds."""
    if not date_str:
        return None
    try:
        return dateparser.parse(date_str)
    except (ValueError, TypeError):
        return None


async def scrape_rss_feed(
    feed_config: dict, max_articles: int = 20
) -> list[Report]:
    """Scrape a single RSS feed and return articles."""
    reports = []
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            response = await client.get(feed_config["url"])
            response.raise_for_status()

        feed = feedparser.parse(response.text)

        for entry in feed.entries[:max_articles]:
            url = entry.get("link", "")
            title = entry.get("title", "")
            if not url or not title:
                continue

            description = entry.get("summary", entry.get("description", ""))
            published = parse_date(entry.get("published", entry.get("updated", "")))

            # ─── Extract media from RSS elements ───
            rss_image = None
            rss_video = None

            # 1. media:content (feedparser normalizes to media_content list)
            media_content = entry.get("media_content", [])
            if isinstance(media_content, list):
                for mc in media_content:
                    mc_url = mc.get("url", "")
                    mc_type = mc.get("type", "").lower()
                    mc_medium = mc.get("medium", "").lower()
                    if not mc_url:
                        continue
                    if mc_type.startswith("video/") or mc_medium == "video":
                        if not rss_video:
                            rss_video = mc_url
                    elif (
                        mc_type.startswith("image/")
                        or mc_medium == "image"
                        or not mc_type
                    ):
                        if not rss_image:
                            rss_image = mc_url

            # 2. media:thumbnail (feedparser normalizes to media_thumbnail list)
            if not rss_image:
                media_thumb = entry.get("media_thumbnail", [])
                if isinstance(media_thumb, list) and media_thumb:
                    thumb_url = media_thumb[0].get("url", "")
                    if thumb_url:
                        rss_image = thumb_url

            # 3. enclosure (feedparser normalizes to links with rel="enclosure")
            for link in entry.get("links", []):
                if link.get("rel") == "enclosure":
                    enc_url = link.get("href", "")
                    enc_type = link.get("type", "").lower()
                    if not enc_url:
                        continue
                    if enc_type.startswith("video/"):
                        if not rss_video:
                            rss_video = enc_url
                    elif enc_type.startswith("image/"):
                        if not rss_image:
                            rss_image = enc_url

            reports.append(
                Report(
                    url=url,
                    title=title,
                    description=description,
                    published_at=published,
                    image_url=rss_image,
                    video_url=rss_video,
                )
            )

        logger.info(f"Scraped {len(reports)} articles from {feed_config['name']}")

    except Exception as e:
        logger.error(f"Error scraping {feed_config['name']}: {e}")

    return reports


async def fetch_og_media(url: str) -> tuple[Optional[str], Optional[str]]:
    """
    Fetch a page and extract og:image and og:video meta tags.
    Uses a lightweight regex approach to avoid heavy HTML parsing dependencies.
    Returns (image_url, video_url) tuple.
    """
    image_url = None
    video_url = None

    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; ConflictMap/1.0)"},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

            html = response.text[:50000]  # Only scan first 50KB

            # ─── og:image ───
            match = re.search(
                r'<meta\s+(?:[^>]*?)property=["\']og:image["\']\s+content=["\']([^"\']+)["\']',
                html,
                re.IGNORECASE,
            )
            if not match:
                match = re.search(
                    r'<meta\s+(?:[^>]*?)content=["\']([^"\']+)["\']\s+(?:[^>]*?)property=["\']og:image["\']',
                    html,
                    re.IGNORECASE,
                )
            if match:
                img = match.group(1).strip()
                if img.startswith(("http://", "https://", "//")):
                    image_url = "https:" + img if img.startswith("//") else img

            # ─── og:video ───
            match = re.search(
                r'<meta\s+(?:[^>]*?)property=["\']og:video(?::url)?["\']\s+content=["\']([^"\']+)["\']',
                html,
                re.IGNORECASE,
            )
            if not match:
                match = re.search(
                    r'<meta\s+(?:[^>]*?)content=["\']([^"\']+)["\']\s+(?:[^>]*?)property=["\']og:video(?::url)?["\']',
                    html,
                    re.IGNORECASE,
                )
            if match:
                vid = match.group(1).strip()
                if vid.startswith(("http://", "https://", "//")):
                    video_url = "https:" + vid if vid.startswith("//") else vid

    except Exception as e:
        logger.debug(f"Failed to fetch og:media from {url}: {e}")

    return image_url, video_url


async def scrape_all_feeds(max_articles_per_feed: int = 20) -> list[Report]:
    """Scrape all configured RSS feeds concurrently."""
    # Scrape all feeds in parallel — each feed handles its own errors
    feed_results = await asyncio.gather(
        *[scrape_rss_feed(fc, max_articles_per_feed) for fc in RSS_FEEDS],
        return_exceptions=True,
    )

    all_reports = []
    for i, result in enumerate(feed_results):
        if isinstance(result, BaseException):
            logger.error(f"Feed {RSS_FEEDS[i]['name']} raised: {result}")
        elif isinstance(result, list):
            all_reports.extend(result)

    # Fetch og:image and og:video for all articles (with concurrency limit)
    # Only fetch for articles that don't already have media from RSS elements
    logger.info(f"Total articles scraped: {len(all_reports)}. Fetching og:media...")

    sem = asyncio.Semaphore(5)  # max 5 concurrent og:media fetches

    async def fetch_media_for(report: Report) -> None:
        async with sem:
            og_image, og_video = await fetch_og_media(report.url)
            # RSS-extracted media takes priority; og:meta is fallback
            if not report.image_url and og_image:
                report.image_url = og_image
            if not report.video_url and og_video:
                report.video_url = og_video

    await asyncio.gather(*[fetch_media_for(a) for a in all_reports])

    images_found = sum(1 for a in all_reports if a.image_url)
    videos_found = sum(1 for a in all_reports if a.video_url)
    logger.info(
        f"Media found: {images_found}/{len(all_reports)} images, "
        f"{videos_found}/{len(all_reports)} videos"
    )

    return all_reports
