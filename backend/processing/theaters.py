"""
Theaters: the named areas where Events cluster, read from `data/theaters.geojson`.

Theaters never overlap, so a point is in at most one. A point outside every
Theater is unassigned (`None`).
"""

import json
from pathlib import Path

from shapely import Point
from shapely.geometry import shape

THEATERS_PATH = Path(__file__).parent.parent.parent / "data" / "theaters.geojson"

_THEATERS = [
    (feature["properties"]["name"], shape(feature["geometry"]))
    for feature in json.loads(THEATERS_PATH.read_text())["features"]
]


def theater_for(lat: float, lng: float) -> str | None:
    """The name of the Theater holding the point, or None; a point on a boundary is inside."""
    point = Point(lng, lat)
    return next((name for name, area in _THEATERS if area.covers(point)), None)


def theater_names() -> list[str]:
    """Every Theater's name, in file order."""
    return [name for name, _ in _THEATERS]
