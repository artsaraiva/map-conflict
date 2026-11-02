"""
Celery worker configuration and task definitions.
Multi-source ingestion: Telegram (every 5 min) + RSS (every 15 min).
"""

import asyncio
from celery import Celery
from celery.schedules import crontab

from backend.core.config import get_settings

settings = get_settings()

app = Celery(
    "geopolitics",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "scrape-telegram-every-5-min": {
            "task": "backend.tasks.worker.scrape_and_process_telegram",
            "schedule": crontab(minute="*/5"),
        },
        "scrape-rss-every-15-min": {
            "task": "backend.tasks.worker.scrape_and_process_rss",
            "schedule": crontab(minute="*/15"),
        },
        # X ingestion runs every 10 minutes when X_BEARER_TOKEN is configured
        "scrape-x-every-10-min": {
            "task": "backend.tasks.worker.scrape_and_process_x",
            "schedule": crontab(minute="*/10"),
        },
        # GDELT is free and requires no auth — runs every 30 minutes
        "scrape-gdelt-every-30-min": {
            "task": "backend.tasks.worker.scrape_and_process_gdelt",
            "schedule": crontab(minute="*/30"),
        },
    },
)


@app.task(name="backend.tasks.worker.scrape_and_process_telegram")
def scrape_and_process_telegram():
    """Celery task that scrapes Telegram channels and processes messages."""
    from backend.processing.pipeline import run_telegram_pipeline

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(run_telegram_pipeline())
        return {"events_processed": result}
    finally:
        loop.close()


@app.task(name="backend.tasks.worker.scrape_and_process_rss")
def scrape_and_process_rss():
    """Celery task that scrapes RSS feeds and processes articles."""
    from backend.processing.pipeline import run_rss_pipeline

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(run_rss_pipeline())
        return {"events_processed": result}
    finally:
        loop.close()


@app.task(name="backend.tasks.worker.scrape_and_process_x")
def scrape_and_process_x():
    """Celery task that scrapes X accounts and processes tweets."""
    from backend.processing.pipeline import run_x_pipeline

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(run_x_pipeline())
        return {"events_processed": result}
    finally:
        loop.close()


@app.task(name="backend.tasks.worker.scrape_and_process_gdelt")
def scrape_and_process_gdelt():
    """Celery task that scrapes GDELT Doc API and processes articles."""
    from backend.processing.pipeline import run_gdelt_pipeline

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(run_gdelt_pipeline())
        return {"events_processed": result}
    finally:
        loop.close()


@app.task(name="backend.tasks.worker.scrape_and_process_all")
def scrape_and_process_all():
    """Celery task that scrapes all sources (Telegram + RSS) concurrently."""
    from backend.processing.pipeline import run_all_sources_pipeline

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(run_all_sources_pipeline())
        return result
    finally:
        loop.close()
