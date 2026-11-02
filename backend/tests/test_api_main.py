"""The Strategic Locations layer and the guarded pipeline trigger."""

import os
import tempfile

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("MEDIA_DIR", tempfile.mkdtemp())  # the app creates its media directory on import
from backend.api.main import app  # noqa: E402
from backend.core.config import get_settings  # noqa: E402

pytestmark = pytest.mark.asyncio


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_strategic_locations_are_served_from_the_curated_file():
    async with _client() as client:
        response = await client.get("/api/strategic-locations")

    assert response.status_code == 200
    assert response.json()["features"], "the curated file is missing or empty"


@pytest.fixture
def trigger_secret(monkeypatch):
    monkeypatch.setattr(get_settings(), "pipeline_trigger_secret", "s3cret")
    return "s3cret"


async def test_trigger_is_off_when_no_secret_is_configured(monkeypatch):
    monkeypatch.setattr(get_settings(), "pipeline_trigger_secret", "")
    async with _client() as client:
        response = await client.post("/api/pipeline/trigger?feed=bogus", headers={"X-Pipeline-Secret": ""})

    assert response.status_code == 403


@pytest.mark.parametrize("headers", [{}, {"X-Pipeline-Secret": "wrong"}])
async def test_trigger_rejects_a_missing_or_wrong_secret(trigger_secret, headers):
    async with _client() as client:
        response = await client.post("/api/pipeline/trigger?feed=bogus", headers=headers)

    assert response.status_code == 403


async def test_trigger_accepts_the_right_secret(trigger_secret):
    # An unknown Feed gets past the secret check and fails validation, so no Feed runs.
    async with _client() as client:
        response = await client.post("/api/pipeline/trigger?feed=bogus", headers={"X-Pipeline-Secret": trigger_secret})

    assert response.status_code == 400
