import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.mars_lookup import lookup_mars

client = TestClient(app)
DATA = Path(__file__).resolve().parents[1] / "app/data/mars"


def test_mars_analog_endpoint_returns_named_candidates_and_exact_evidence():
    response = client.post("/terrain/analogs", json={"planet": "mars", "lat": 18.44, "lon": 77.45})
    assert response.status_code == 200
    result = response.json()
    assert result["body"] == "mars"
    assert len(result["candidates"]) == 3
    assert result["climate"]["precipitation"] is None
    for site in result["candidates"]:
        assert site["location"]["country"]
        contributions = site["match_explanation"]["comparisons"]
        assert abs(sum(row["squared_distance_contribution"] for row in contributions) - site["distance"] ** 2) < 1e-7


def test_mars_model_handles_poles_and_longitude_wrap():
    for lat in [-90, 0, 90]:
        for lon in [-180, 0, 180]:
            a = lookup_mars(lat, lon, DATA)
            b = lookup_mars(lat, lon + 360, DATA)
            assert a == b


def test_all_types_are_reachable_and_have_three_candidates():
    catalog = json.loads((DATA / "mars_types.json").read_text())
    labels = (DATA / "mars_types_grid.bin").read_bytes()
    assert len(labels) == 720 * 360
    assert set(labels) == set(range(10))
    assert all(len(t["earth_candidates"]) == 3 for t in catalog["types"])


def test_analog_endpoint_validates_input_and_does_not_apply_mars_to_moon():
    for payload in [
        {"planet": "moon", "lat": 0, "lon": 0},
        {"lat": 91, "lon": 0}, {"lat": 0, "lon": 361},
        {"lat": "18", "lon": 20}, {"lat": None, "lon": 0},
    ]:
        assert client.post("/terrain/analogs", json=payload).status_code == 422


def test_analog_endpoint_is_documented():
    assert "post" in client.get("/openapi.json").json()["paths"]["/terrain/analogs"]
