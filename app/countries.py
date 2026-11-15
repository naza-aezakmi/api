"""Offline point-in-polygon country labels, without third-party geocoding calls."""
import gzip
import json
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=1)
def boundaries():
    with gzip.open(Path(__file__).parent / "data/environment/countries.json.gz", "rt") as stream:
        return json.load(stream)


def inside(x, y, ring):
    result = False
    previous = ring[-1]
    for current in ring:
        if (current[1] > y) != (previous[1] > y) and x < (previous[0] - current[0]) * (y - current[1]) / (previous[1] - current[1]) + current[0]:
            result = not result
        previous = current
    return result


def country_at(lat, lon):
    lon = (lon + 180) % 360 - 180
    for polygon in boundaries()["polygons"]:
        west, south, east, north = polygon["bounds"]
        if west <= lon <= east and south <= lat <= north:
            rings = polygon["rings"]
            if inside(lon, lat, rings[0]) and not any(inside(lon, lat, hole) for hole in rings[1:]):
                return {"country": polygon["country"], "country_code": polygon["code"]}
    return {"country": None, "country_code": None}
