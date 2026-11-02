"""Theaters: which named Theater, if any, holds a place."""

import json
from itertools import combinations

from shapely.geometry import shape

from backend.processing.theaters import THEATERS_PATH, theater_for


def test_gaza_city_is_in_gaza():
    assert theater_for(31.50, 34.47) == "Gaza"


def test_point_midway_between_taiwan_and_fujian_is_in_the_taiwan_strait():
    assert theater_for(24.5, 119.6) == "Taiwan Strait"


def test_paris_and_the_open_atlantic_are_in_no_theater():
    assert theater_for(48.86, 2.35) is None
    assert theater_for(30.0, -40.0) is None


def test_point_on_a_theater_boundary_is_in_that_theater():
    # The West Bank's southern edge runs along latitude 31.35.
    assert theater_for(31.35, 35.25) == "West Bank"


def test_theater_data_is_valid_uniquely_named_and_never_overlaps():
    features = json.loads(THEATERS_PATH.read_text())["features"]
    theaters = [(f["properties"]["name"], shape(f["geometry"])) for f in features]
    names = [name for name, _ in theaters]

    assert [name for name, area in theaters if not area.is_valid] == []
    assert len(names) == len(set(names))
    assert [
        (a, b)
        for (a, area_a), (b, area_b) in combinations(theaters, 2)
        if area_a.intersects(area_b)
    ] == []
