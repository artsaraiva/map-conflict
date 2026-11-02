"""
X (Twitter) scraper stub.

Monitors analyst, journalist, and official accounts for geopolitical signals.
Requires X API v2 Bearer Token configured via X_BEARER_TOKEN environment variable.

Returns Reports like every other Feed adapter.
"""

import logging
import os

from backend.scraping.report import Report

logger = logging.getLogger(__name__)

# Curated accounts to monitor (handles without @)
X_ACCOUNTS = [
    "KyivIndependent",
    "RALee85",          # military analyst
    "DAlperovitch",     # geopolitics/security
    "michaelkofman",    # Russia/military analyst
    "ELINTNews",
    "OSINTdefender",
    "GeoConfirmed",
    "ASBMilitary",
]

# Number of recent tweets to fetch per account
MAX_TWEETS_PER_ACCOUNT = 10


async def scrape_x_accounts(
    max_per_account: int = MAX_TWEETS_PER_ACCOUNT,
) -> list[Report]:
    """
    Fetch recent tweets from monitored accounts and return them as Reports.

    Requires X_BEARER_TOKEN in the environment.  Returns an empty list and logs
    a warning if the token is not configured, so the pipeline degrades gracefully.
    """
    bearer_token = os.environ.get("X_BEARER_TOKEN", "").strip()
    if not bearer_token:
        logger.warning(
            "X_BEARER_TOKEN not set — skipping X ingestion. "
            "Set the environment variable to enable this source."
        )
        return []

    try:
        import httpx
    except ImportError:
        logger.error("httpx not installed — cannot scrape X. Add it to requirements.")
        return []

    reports: list[Report] = []
    headers = {"Authorization": f"Bearer {bearer_token}"}

    async with httpx.AsyncClient(timeout=30) as client:
        for handle in X_ACCOUNTS:
            try:
                # Resolve user ID
                user_resp = await client.get(
                    f"https://api.twitter.com/2/users/by/username/{handle}",
                    headers=headers,
                )
                if user_resp.status_code != 200:
                    logger.warning(
                        f"X: could not resolve @{handle} (status {user_resp.status_code})"
                    )
                    continue

                user_id = user_resp.json()["data"]["id"]

                # Fetch recent tweets
                tweets_resp = await client.get(
                    f"https://api.twitter.com/2/users/{user_id}/tweets",
                    headers=headers,
                    params={
                        "max_results": max_per_account,
                        "tweet.fields": "created_at,text",
                        "expansions": "author_id",
                    },
                )
                if tweets_resp.status_code != 200:
                    logger.warning(
                        f"X: failed to fetch tweets for @{handle} "
                        f"(status {tweets_resp.status_code})"
                    )
                    continue

                tweets = tweets_resp.json().get("data", [])
                for tweet in tweets:
                    tweet_id = tweet["id"]
                    text = tweet.get("text", "")
                    created_at_raw = tweet.get("created_at")

                    try:
                        from dateutil import parser as dateparser
                        created_at = dateparser.parse(created_at_raw) if created_at_raw else None
                    except Exception:
                        created_at = None

                    reports.append(
                        Report(
                            url=f"https://twitter.com/{handle}/status/{tweet_id}",
                            title=text[:200],
                            description=text,
                            published_at=created_at,
                            image_url=None,
                            video_url=None,
                        )
                    )

            except Exception as e:
                logger.error(f"X: error scraping @{handle}: {e}")
                continue

    logger.info(f"X scraper fetched {len(reports)} tweets from {len(X_ACCOUNTS)} accounts")
    return reports
