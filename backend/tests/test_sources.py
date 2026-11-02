"""Source identity drives Corroboration: same Source via any Feed must yield one key."""

import asyncio
from datetime import datetime, timezone

import httpx

from backend.scraping.gdelt_scraper import _scrape_gdelt_query
from backend.scraping.sources import source_key

# GDELT Doc API `artlist` response shape (hand-written sample, not a live capture).
GDELT_ARTLIST = {
    "articles": [
        {
            "url": "https://www.bbc.com/news/articles/c123",
            "url_mobile": "",
            "title": "Houthis claim strike on tanker in Red Sea",
            "seendate": "20261102T091500Z",
            "socialimage": "https://ichef.bbci.co.uk/news/1024/tanker.jpg",
            "domain": "bbc.com",
            "language": "English",
            "sourcecountry": "United Kingdom",
        },
        {
            "url": "https://www.reuters.com/world/middle-east/tanker-2026-11-02/",
            "url_mobile": "",
            "title": "Tanker reports explosion off Yemen",
            "seendate": "20261102T093000Z",
            "socialimage": "",
            "domain": "reuters.com",
            "language": "English",
            "sourcecountry": "United States",
        },
        {
            "url": "https://www.lemonde.fr/international/article/x",
            "title": "Mer Rouge : un pétrolier touché",
            "seendate": "20261102T094500Z",
            "domain": "lemonde.fr",
            "language": "French",
        },
    ]
}


def test_source_key_is_canonical_web_address():
    assert source_key("https://www.bbc.co.uk/news/world-1") == "bbc.co.uk"
    assert source_key("https://www.BBC.com/news/articles/c1") == "bbc.co.uk"  # alias
    assert source_key("https://apnews.com/article/x") == "apnews.com"
    assert source_key("bbc.com") == "bbc.co.uk"  # bare domain, as GDELT gives it
    assert source_key("https://t.me/RNintel/4242") == "t.me/rnintel"
    assert source_key("https://twitter.com/OSINTdefender/status/1") == "x.com/osintdefender"
    assert source_key("https://x.com/OSINTdefender") == "x.com/osintdefender"
    # Without an alias, the same name on two platforms is two addresses, so two keys.
    assert source_key("https://t.me/rnintel/1") != source_key("https://x.com/rnintel/status/1")


def test_gdelt_reports_carry_their_real_source_and_utc_time():
    transport = httpx.MockTransport(lambda req: httpx.Response(200, json=GDELT_ARTLIST))

    async def fetch():
        async with httpx.AsyncClient(transport=transport) as client:
            return await _scrape_gdelt_query({"query": "Red Sea", "max": 10}, client)

    reports = asyncio.run(fetch())

    assert [r.source for r in reports] == ["bbc.com", "reuters.com"]  # raw `domain`; French dropped
    bbc = reports[0]
    assert bbc.image_url == "https://ichef.bbci.co.uk/news/1024/tanker.jpg"
    assert reports[1].image_url is None
    assert bbc.published_at == datetime(2026, 11, 2, 9, 15, tzinfo=timezone.utc)
