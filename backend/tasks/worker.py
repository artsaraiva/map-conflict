"""
Celery worker: one task, `ingest_feed(name)`, scheduled per Feed by beat.
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

# Feed name -> minutes between runs. X is a no-op until X_BEARER_TOKEN is set.
FEED_SCHEDULE = {"telegram": 5, "x": 10, "rss": 15, "gdelt": 30}

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        f"ingest-{feed}-every-{minutes}-min": {
            "task": "backend.tasks.worker.ingest_feed",
            "schedule": crontab(minute=f"*/{minutes}"),
            "args": (feed,),
        }
        for feed, minutes in FEED_SCHEDULE.items()
    },
)


@app.task(name="backend.tasks.worker.ingest_feed")
def ingest_feed(name: str):
    """Fetch one Feed and process its Reports."""
    from backend.processing.pipeline import run_feed

    return {"events_processed": asyncio.run(run_feed(name))}
