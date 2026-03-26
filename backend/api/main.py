import os
from pathlib import Path

from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.events import router as events_router

app = FastAPI(
    title="Geopolitics Map API",
    description="Live geopolitical event tracking and map visualization",
    version="0.1.0",
)

# CORS - allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events_router)

# ── Static media serving (Telegram thumbnails etc.) ─────────────────────────
# The media directory is shared between the worker (downloads) and backend
# (serves) via a Docker volume mounted at /app/media.
MEDIA_DIR = os.environ.get("MEDIA_DIR", "/app/media")
media_path = Path(MEDIA_DIR)
media_path.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(media_path)), name="media")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/pipeline/trigger")
async def trigger_pipeline(background_tasks: BackgroundTasks):
    """Manually trigger the full multi-source pipeline (Telegram + RSS)."""
    from backend.processing.pipeline import run_all_sources_pipeline

    background_tasks.add_task(run_all_sources_pipeline)
    return {"status": "pipeline triggered (all sources)"}


@app.post("/api/pipeline/trigger-telegram")
async def trigger_telegram_pipeline(background_tasks: BackgroundTasks):
    """Manually trigger only the Telegram scraping pipeline."""
    from backend.processing.pipeline import run_telegram_pipeline

    background_tasks.add_task(run_telegram_pipeline)
    return {"status": "pipeline triggered (telegram)"}


@app.post("/api/pipeline/trigger-rss")
async def trigger_rss_pipeline(background_tasks: BackgroundTasks):
    """Manually trigger only the RSS scraping pipeline."""
    from backend.processing.pipeline import run_rss_pipeline

    background_tasks.add_task(run_rss_pipeline)
    return {"status": "pipeline triggered (rss)"}
