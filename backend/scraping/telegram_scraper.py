"""
Telegram channel scraper using Telethon.

Polls configured public Telegram channels for new messages, downloads photo
thumbnails to a local directory, and returns Report objects compatible
with the existing processing pipeline.

Requires TELEGRAM_API_ID, TELEGRAM_API_HASH, and TELEGRAM_SESSION env vars.
If any are missing the scraper gracefully returns an empty list.
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl.types import (
    MessageMediaPhoto,
    MessageMediaDocument,
    DocumentAttributeVideo,
)

from backend.core.config import get_settings
from backend.scraping.report import Report

logger = logging.getLogger(__name__)

# ── Channel configuration ───────────────────────────────────────────────────
# Public channel usernames. Each channel's Source key is t.me/<username>.
TELEGRAM_CHANNELS = [
    "FrontlineReportNews",
    "BellumActaNews",
    "rnintel",
    "tglobaleye",
    "tupireport",
    "disclosetv",
]


def _get_client() -> Optional[TelegramClient]:
    """
    Build a Telethon client from settings.
    Returns None if Telegram is not configured (graceful degradation).
    """
    settings = get_settings()

    if (
        not settings.telegram_api_id
        or not settings.telegram_api_hash
        or not settings.telegram_session
    ):
        logger.info(
            "Telegram scraper disabled — TELEGRAM_API_ID, TELEGRAM_API_HASH, "
            "or TELEGRAM_SESSION not set."
        )
        return None

    return TelegramClient(
        StringSession(settings.telegram_session),
        settings.telegram_api_id,
        settings.telegram_api_hash,
        flood_sleep_threshold=120,
        receive_updates=False,
    )


def _extract_title(text: Optional[str], max_len: int = 120) -> str:
    """
    Extract a title from the message text.
    Uses the first line if short enough, otherwise truncates with ellipsis.
    """
    if not text:
        return "Telegram post"

    # Take first line (split on newline)
    first_line = text.strip().split("\n")[0].strip()

    # Remove leading emoji / special chars for a cleaner title
    # but keep the substance
    if len(first_line) <= max_len:
        return first_line

    return first_line[: max_len - 1] + "\u2026"


def _has_video(message) -> bool:
    """Check if a Telegram message contains a video."""
    if not message.media:
        return False

    if isinstance(message.media, MessageMediaDocument) and message.media.document:
        for attr in message.media.document.attributes:
            if isinstance(attr, DocumentAttributeVideo):
                return True

    return False


def _get_video_size(message) -> int:
    """Get the video file size in bytes. Returns 0 if not a video."""
    if not message.media or not isinstance(message.media, MessageMediaDocument):
        return 0
    doc = message.media.document
    if doc and doc.size:
        return doc.size
    return 0


async def _download_photo(
    client: TelegramClient,
    message,
    channel_username: str,
    media_dir: str,
) -> Optional[str]:
    """
    Download the photo from a message.
    Returns the relative URL path (e.g. /media/telegram/channel_123.jpg)
    or None if no photo / download fails.
    """
    if not message.photo:
        return None

    # Ensure the media directory exists
    Path(media_dir).mkdir(parents=True, exist_ok=True)

    filename = f"{channel_username}_{message.id}.jpg"
    filepath = os.path.join(media_dir, filename)

    # Skip if already downloaded (idempotent)
    if os.path.exists(filepath):
        return f"/media/telegram/{filename}"

    try:
        await client.download_media(
            message,
            file=filepath,
            thumb=-1,  # Download the largest available thumbnail
        )
        logger.debug(f"Downloaded photo: {filename}")
        return f"/media/telegram/{filename}"
    except Exception as e:
        logger.warning(f"Failed to download photo {filename}: {e}")
        return None


async def _download_video(
    client: TelegramClient,
    message,
    channel_username: str,
    media_dir: str,
    max_size_mb: int = 50,
    timeout_seconds: int = 30,
) -> tuple[Optional[str], Optional[str]]:
    """
    Download a video file and its thumbnail from a Telegram message.

    Returns (video_url, thumb_url) tuple:
      - video_url: relative URL path to the .mp4 file, or t.me fallback, or None
      - thumb_url: relative URL path to the video thumbnail .jpg, or None

    Applies a per-file timeout to avoid blocking the scrape loop on large files.
    """
    if not _has_video(message):
        return None, None

    # Check file size before downloading
    size_bytes = _get_video_size(message)
    max_bytes = max_size_mb * 1024 * 1024
    if size_bytes > max_bytes:
        size_mb = size_bytes / (1024 * 1024)
        logger.info(
            f"Skipping video {channel_username}_{message.id}: "
            f"{size_mb:.1f}MB exceeds {max_size_mb}MB limit"
        )
        # Still return the t.me link as fallback
        return f"https://t.me/{channel_username}/{message.id}", None

    Path(media_dir).mkdir(parents=True, exist_ok=True)

    video_filename = f"{channel_username}_{message.id}.mp4"
    video_filepath = os.path.join(media_dir, video_filename)
    video_url = None
    thumb_url = None
    fallback_url = f"https://t.me/{channel_username}/{message.id}"

    # Download the full video file (idempotent, with timeout)
    if os.path.exists(video_filepath):
        video_url = f"/media/telegram/{video_filename}"
    else:
        try:
            await asyncio.wait_for(
                client.download_media(
                    message,
                    file=video_filepath,
                    # No thumb param = download full media file
                ),
                timeout=timeout_seconds,
            )
            logger.debug(f"Downloaded video: {video_filename}")
            video_url = f"/media/telegram/{video_filename}"
        except asyncio.TimeoutError:
            logger.warning(
                f"Video download timed out after {timeout_seconds}s: {video_filename} — using t.me link"
            )
            # Clean up partial file
            if os.path.exists(video_filepath):
                os.remove(video_filepath)
            video_url = fallback_url
        except Exception as e:
            logger.warning(f"Failed to download video {video_filename}: {e}")
            if os.path.exists(video_filepath):
                os.remove(video_filepath)
            video_url = fallback_url

    # Download video thumbnail as preview image (fast, small file)
    thumb_filename = f"{channel_username}_{message.id}_thumb.jpg"
    thumb_filepath = os.path.join(media_dir, thumb_filename)

    if os.path.exists(thumb_filepath):
        thumb_url = f"/media/telegram/{thumb_filename}"
    else:
        try:
            await asyncio.wait_for(
                client.download_media(
                    message,
                    file=thumb_filepath,
                    thumb=-1,  # Largest thumbnail
                ),
                timeout=10,
            )
            if os.path.exists(thumb_filepath) and os.path.getsize(thumb_filepath) > 0:
                logger.debug(f"Downloaded video thumbnail: {thumb_filename}")
                thumb_url = f"/media/telegram/{thumb_filename}"
        except (asyncio.TimeoutError, Exception) as e:
            logger.debug(f"No thumbnail for video {video_filename}: {e}")

    return video_url, thumb_url


async def scrape_telegram_channels() -> list[Report]:
    """
    Scrape all configured Telegram channels and return Report objects.

    - Connects via StringSession (no interactive auth needed)
    - Fetches the latest N messages from each channel
    - Downloads photo thumbnails to the local media directory
    - Maps each message to a Report for the processing pipeline
    - Gracefully returns [] if Telegram is not configured
    """
    settings = get_settings()

    # Build channel list from settings (allows override via env var)
    channels = [
        ch.strip() for ch in settings.telegram_channels.split(",") if ch.strip()
    ] or TELEGRAM_CHANNELS

    client = _get_client()
    if client is None:
        return []

    media_dir = settings.telegram_media_dir
    max_messages = settings.telegram_max_messages
    all_reports: list[Report] = []

    try:
        await client.start()
        logger.info(f"Telegram client connected. Scraping {len(channels)} channels...")

        for username in channels:

            try:
                messages = await client.get_messages(username, limit=max_messages)
                logger.info(f"Fetched {len(messages)} messages from @{username}")

                processed = 0
                for msg in messages:
                    # Skip messages with no text (media-only with no caption)
                    text = msg.text or msg.message or ""
                    if not text.strip():
                        continue

                    # Build stable dedup URL
                    url = f"https://t.me/{username}/{msg.id}"

                    # Extract title from first line of text
                    title = _extract_title(text)

                    # Published timestamp
                    published_at = msg.date

                    # Download photo if present
                    image_url = await _download_photo(client, msg, username, media_dir)

                    # Download video file + thumbnail if present
                    video_url = None
                    if _has_video(msg):
                        max_video_mb = settings.telegram_max_video_size_mb
                        video_url, thumb_url = await _download_video(
                            client, msg, username, media_dir, max_video_mb
                        )
                        # Use video thumbnail as image if no photo was present
                        if not image_url and thumb_url:
                            image_url = thumb_url

                    report = Report(
                        url=url,
                        title=title,
                        description=text,
                        published_at=published_at,
                        image_url=image_url,
                        video_url=video_url,
                    )
                    all_reports.append(report)
                    processed += 1

                logger.info(f"@{username}: processed {processed} messages with text")

            except Exception as e:
                logger.error(f"Error scraping @{username}: {e}")

            # Small delay between channels to respect rate limits
            await asyncio.sleep(2)

    except Exception as e:
        logger.error(f"Telegram client error: {e}")
    finally:
        await client.disconnect()

    images_count = sum(1 for a in all_reports if a.image_url)
    videos_count = sum(1 for a in all_reports if a.video_url)
    logger.info(
        f"Telegram scrape complete: {len(all_reports)} messages, "
        f"{images_count} photos, {videos_count} videos"
    )

    return all_reports
