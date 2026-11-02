"""
Geocoding service: resolves location names to coordinates.
First checks the curated Strategic Locations, then falls back to Nominatim.
"""

import asyncio
import json
import httpx
import logging
import re
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

STRATEGIC_LOCATIONS_PATH = Path(__file__).parent.parent.parent / "data" / "strategic_locations.geojson"

# Regex to detect strings that are mostly non-Latin (emoji flags, CJK, etc.)
_NON_GEOCODABLE = re.compile(r"^[\W\d_]+$", re.UNICODE)


@dataclass
class GeocodedLocation:
    name: str
    latitude: float
    longitude: float
    display_name: str = ""


# In-memory cache for Strategic Locations, keyed by lowercase name and alias
_strategic_locations_cache: dict[str, GeocodedLocation] = {}

# In-memory cache for Nominatim results (avoids re-querying same location)
_nominatim_cache: dict[str, Optional[GeocodedLocation]] = {}

# Simple lock to serialize Nominatim calls (respect 1 req/s rate limit)
_nominatim_lock = asyncio.Lock()


def _load_strategic_locations() -> dict[str, GeocodedLocation]:
    """Load the curated Strategic Locations from GeoJSON."""
    global _strategic_locations_cache
    if _strategic_locations_cache:
        return _strategic_locations_cache

    try:
        with open(STRATEGIC_LOCATIONS_PATH) as f:
            data = json.load(f)

        for feature in data.get("features", []):
            props = feature.get("properties", {})
            name = props.get("name", "").lower()
            coords = feature.get("geometry", {}).get("coordinates", [])

            # For points: [lng, lat]; for polygons: use centroid from properties
            if feature["geometry"]["type"] == "Point":
                lng, lat = coords
            else:
                lat = props.get("centroid_lat", 0)
                lng = props.get("centroid_lng", 0)

            if name and lat and lng:
                aliases = [name] + [a.lower() for a in props.get("aliases", [])]
                for alias in aliases:
                    _strategic_locations_cache[alias] = GeocodedLocation(
                        name=props.get("name", name),
                        latitude=lat,
                        longitude=lng,
                        display_name=props.get("display_name", name),
                    )

        logger.info(f"Loaded {len(_strategic_locations_cache)} Strategic Location entries")
    except FileNotFoundError:
        logger.warning("Strategic Locations GeoJSON not found, using Nominatim only")
    except Exception as e:
        logger.error(f"Error loading Strategic Locations: {e}")

    return _strategic_locations_cache


async def geocode_nominatim(location: str) -> Optional[GeocodedLocation]:
    """Geocode a location using OpenStreetMap Nominatim (free, rate-limited)."""
    # Check cache first
    cache_key = location.lower().strip()
    if cache_key in _nominatim_cache:
        return _nominatim_cache[cache_key]

    # Serialize requests and add delay to respect Nominatim's 1 req/s limit
    async with _nominatim_lock:
        # Double-check cache after acquiring lock
        if cache_key in _nominatim_cache:
            return _nominatim_cache[cache_key]

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://nominatim.openstreetmap.org/search",
                    params={
                        "q": location,
                        "format": "json",
                        "limit": 1,
                        "addressdetails": 0,
                    },
                    headers={"User-Agent": "GeopoliticsMap/0.1 (educational project)"},
                )
                response.raise_for_status()
                results = response.json()

                if results:
                    result = results[0]
                    geo = GeocodedLocation(
                        name=location,
                        latitude=float(result["lat"]),
                        longitude=float(result["lon"]),
                        display_name=result.get("display_name", location),
                    )
                    _nominatim_cache[cache_key] = geo
                    # Rate limit: wait 1.1s before next request
                    await asyncio.sleep(1.1)
                    return geo

                _nominatim_cache[cache_key] = None
                await asyncio.sleep(1.1)
        except Exception as e:
            logger.error(f"Nominatim geocoding error for '{location}': {e}")
            _nominatim_cache[cache_key] = None

    return None


async def geocode_location(location: str) -> Optional[GeocodedLocation]:
    """
    Geocode a location name. Checks the curated Strategic Locations first,
    then falls back to Nominatim.
    """
    # Skip junk locations (emoji flags, punctuation-only strings, single chars)
    stripped = location.strip()
    if len(stripped) < 2 or _NON_GEOCODABLE.match(stripped):
        logger.debug(f"Skipping non-geocodable location: '{location}'")
        return None

    # Check the curated Strategic Locations first
    locations = _load_strategic_locations()
    key = stripped.lower()

    if key in locations:
        logger.debug(f"Strategic Location hit for '{location}'")
        return locations[key]

    # Check partial matches (e.g., "strait of hormuz" in "the strait of hormuz area")
    for location_key, geo in locations.items():
        if location_key in key or key in location_key:
            logger.debug(f"Partial Strategic Location match: '{location}' -> '{location_key}'")
            return geo

    # Fall back to Nominatim
    return await geocode_nominatim(location)
