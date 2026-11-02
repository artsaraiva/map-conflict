import os
import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from backend.api.events import router as events_router
from backend.processing.theaters import theater_names

app = FastAPI(
    title="Geopolitics Map API",
    description="Live geopolitical event tracking and map visualization",
    version="0.1.0",
)

# CORS - allow frontend to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(events_router)

# ── Strategic hotspots GeoJSON ───────────────────────────────────────────────
_HOTSPOTS_FILE = Path(__file__).parent.parent.parent / "data" / "hotspots.geojson"


@app.get("/api/hotspots", response_class=JSONResponse)
async def get_strategic_hotspots():
    """Serve the curated strategic locations GeoJSON as a static map layer."""
    if not _HOTSPOTS_FILE.exists():
        return JSONResponse({"type": "FeatureCollection", "features": []})
    with open(_HOTSPOTS_FILE) as f:
        data = json.load(f)
    return JSONResponse(data)


@app.get("/api/theaters", response_model=list[str])
async def get_theaters():
    """The Theater names, in file order."""
    return theater_names()


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
async def trigger_pipeline(background_tasks: BackgroundTasks, feed: Optional[str] = None):
    """Run one Feed (`?feed=telegram|rss|x|gdelt`) or, with no `feed`, all of them."""
    from backend.processing.pipeline import FEEDS, run_all_feeds, run_feed

    if feed is None:
        background_tasks.add_task(run_all_feeds)
    elif feed in FEEDS:
        background_tasks.add_task(run_feed, feed)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown feed {feed!r}; expected one of {list(FEEDS)}")
    return {"status": f"pipeline triggered ({feed or 'all feeds'})"}
