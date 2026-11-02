# Geopolitics Map - Live Conflict Tracker

A live, interactive geopolitical map that scrapes news and visualizes world events
in a grand-strategy-game style interface.

## One-Command Docker Start

### Prerequisites
- Docker & Docker Compose

### 1. Configure environment
```bash
cp .env.example .env
```

Fill in:
- `OPENAI_API_KEY` - for article classification/summarization
- `NEXT_PUBLIC_MAPTILER_API_KEY` - for map tiles

### 2. Start the full stack
```bash
docker compose up --build
```

Services started:
- frontend: `http://localhost:3001`
- backend API: `http://localhost:8000`
- postgres with PostGIS
- redis
- celery worker + beat

The backend container auto-initializes the database schema and enables the PostGIS extension on startup.

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.12+
- Node.js 20+

### 1. Start infrastructure
```bash
docker compose up -d
```

### 2. Start backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Run migrations
alembic upgrade head

# Start API server
uvicorn api.main:app --reload --port 8000

# In another terminal - start Celery worker
celery -A tasks.worker worker --loglevel=info --beat
```

### Run the backend tests
With the stack up (`docker compose up -d`), run the tests inside the backend container:
```bash
docker compose exec backend sh -c "pip install -q -r backend/requirements-dev.txt && python -m pytest backend/tests -q"
```
The image bakes in the source, so run `docker compose up -d --build backend` after editing code or tests. Tests use their own database, `geopolitics_test`, on the same PostGIS server, so your data is never touched.

### Reassign Theaters
Theaters are the named places in `data/theaters.geojson`. Intake gives each new Event the Theater that holds it. Stored Events keep theirs until you reassign them, so run this once after pulling the named-Theater change, and again after any edit to `data/theaters.geojson`:
```bash
docker compose exec backend python backend/scripts/reassign_theaters.py
```
Running it twice changes nothing. Rebuild the backend image first (`docker compose up -d --build backend`) so it sees the edited file.

### 3. Start frontend
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3001

## Environment Variables

Copy `.env.example` to `.env` and fill in:
- `OPENAI_API_KEY` - for article classification/summarization
- `NEXT_PUBLIC_MAPTILER_API_KEY` - for map tiles (free tier at maptiler.com)
