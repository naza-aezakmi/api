import json
from pathlib import Path
from urllib.error import URLError

import pytest
from fastapi.testclient import TestClient

from app import environment
from app.countries import country_at
from app.main import app

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def reset_environment_caches():
    environment.earth_passport.cache_clear()
    environment.moon_cell_passport.cache_clear()
    yield
    environment.earth_passport.cache_clear()
    environment.moon_cell_passport.cache_clear()


@pytest.mark.parametrize("lat,lon,country", [(31.701, 59.352, "Iran"), (39.74, -104.99, "United States of America"), (27.369, -107.577, "Mexico"), (-85, 0, "Antarctica"), (52.52, 13.405, "Germany")])
def test_country_names_are_resolved_offline(lat, lon, country):
    assert country_at(lat, lon)["country"] == country
    assert country_at(lat, lon + 360)["country"] == country


def test_ocean_does_not_get_an_invented_country():
    assert country_at(0, 0)["country"] is None


def test_earth_units_monthly_means_and_missing_values(monkeypatch):
    data = json.loads((FIXTURES / "power_climatology.json").read_text())
    data["properties"]["parameter"]["RH2M"]["ANN"] = 0
    data["properties"]["parameter"]["PRECTOTCORR"]["ANN"] = -999
    monkeypatch.setattr(environment, "read_url", lambda *a, **kw: json.dumps(data).encode())
    passport = environment.earth_passport(31.701, 59.352)
    metrics = {m["id"]: m["value"] for m in passport["metrics"]}
    assert metrics["pressure_pa"] == 87650
    assert metrics["relative_humidity_pct"] == 0
    assert metrics["precipitation_mm_day"] is None
    assert metrics["coldest_month_c"] == 6.81
    assert metrics["warmest_month_c"] == 31.48
    assert passport["status"] == "partial"
    assert "2001" in passport["source"]["period"]


def test_diviner_byte_indexing_temperatures_and_coverage(monkeypatch):
    def read(url, *, headers, limit):
        assert "00n10n" in url
        expected_start = 113 + (406 * 20 + 1) * 96 * 113
        assert headers == {"Range": f"bytes={expected_start}-{expected_start + 96 * 113 - 1}"}
        assert limit == 96 * 113
        return (FIXTURES / "diviner_apollo_cell.txt").read_bytes()
    monkeypatch.setattr(environment, "read_url", read)
    passport = environment.moon_cell_passport(*environment.moon_cell(.674, 23.473))
    assert passport["coverage"] == {"valid_bins": 53, "total_bins": 96}
    metrics = {m["id"]: m["value"] for m in passport["metrics"]}
    assert metrics["surface_temperature_min_c"] == -177.9
    assert metrics["surface_temperature_max_c"] == 122.4
    assert passport["sampled_location"]["lat"] == .75
    assert passport["sampled_location"]["lon"] == 23.25


def test_diviner_rejects_wrong_spatial_cell(monkeypatch):
    monkeypatch.setattr(environment, "read_url", lambda *a, **kw: (FIXTURES / "diviner_apollo_cell.txt").read_bytes())
    with pytest.raises(ValueError, match="coordinates"):
        environment.moon_cell_passport(0, 0, 0)


def test_poles_dateline_and_missing_mars_values():
    assert environment.moon_cell(90, 180) == (80, 19, 0)
    assert environment.moon_cell(-90, -180) == (-90, 0, 0)
    assert environment.moon_cell(0, 360) == environment.moon_cell(0, 0)
    a, b = environment.mars_passport(18.445, 77.451), environment.mars_passport(18.445, 437.451)
    assert a == b
    metrics = {m["id"]: m["value"] for m in a["metrics"]}
    assert metrics["relative_humidity_pct"] is None
    assert metrics["precipitation_mm_day"] is None


def test_failed_upstream_is_not_reported_as_zero_temperature(monkeypatch):
    def broken(*a, **kw):
        raise URLError("offline")
    monkeypatch.setattr(environment, "read_url", broken)
    passport = environment.safe_passport("earth", 20, 30)
    assert passport["status"] == "unavailable"
    assert passport["metrics"] == []


def test_pds_ignoring_range_is_rejected_before_reading(monkeypatch):
    class Response:
        status = 200
        headers = {}
        def __enter__(self): return self
        def __exit__(self, *a): return None
        def read(self, size): raise AssertionError("Must not read the full PDS table")
    monkeypatch.setattr(environment, "urlopen", lambda *a, **kw: Response())
    with pytest.raises(ValueError, match="byte range"):
        environment.read_url("https://example.invalid/file", headers={"Range": "bytes=113-225"}, limit=113)


def test_context_is_separate_from_ranking_and_validates_coordinates(monkeypatch):
    monkeypatch.setattr(environment, "safe_passport", lambda body, lat, lon: {"body": body, "status": "available", "metrics": [], "notes": []})
    with TestClient(app) as client:
        response = client.post("/terrain/context", json={"planet": "mars", "lat": 18.445, "lon": 77.451, "earth_lat": 31.701, "earth_lon": 59.352})
        assert response.status_code == 200
        assert response.json()["used_in_ranking"] is False
        assert response.json()["reference"]["body"] == "mars"
        assert response.json()["earth"]["body"] == "earth"
        bad = client.post("/terrain/context", json={"planet": "moon", "lat": 91, "lon": 0, "earth_lat": 0, "earth_lon": 0})
        assert bad.status_code == 422
