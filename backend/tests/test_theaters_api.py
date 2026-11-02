"""The Theater list the API serves."""

import os
import tempfile

import pytest
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("MEDIA_DIR", tempfile.mkdtemp())  # the app creates its media directory on import
from backend.api.main import app  # noqa: E402

pytestmark = pytest.mark.asyncio


async def test_theaters_are_listed_by_name_in_file_order():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/theaters")

    assert response.status_code == 200
    assert response.json() == [
        "Donbas",
        "Crimea and Black Sea",
        "Gaza",
        "West Bank",
        "Lebanon–Israel Border",
        "Syria",
        "Red Sea and Bab el-Mandeb",
        "Persian Gulf and Hormuz",
        "Taiwan Strait",
        "South China Sea",
        "Korean Peninsula",
        "Kashmir",
        "Sudan",
        "Eastern Congo",
        "Sahel",
    ]
