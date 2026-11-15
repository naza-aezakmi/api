import math

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.terrain_engine import TerrainEngine


@pytest.mark.parametrize("planet,coordinates,label", [
    ("moon", (0.674, 23.473), "NASA LRO LOLA"),
    ("mars", (18.445, 77.451), "NASA MGS MOLA"),
])
def test_objective_weights_rank_ten_candidates_from_each_planet(planet, coordinates, label, monkeypatch):
    monkeypatch.setattr('app.terrain_search.engine', TerrainEngine())
    orders = [
        ["slope", "roughness", "profile", "range"],
        ["profile", "range", "slope", "roughness"],
    ]
    results = []
    # Keep the persistent worker and its asyncio lock on one test-client loop.
    with TestClient(app) as client:
        for order in orders:
            response = client.post("/terrain/search", json={
                "planet": planet, "lat": coordinates[0], "lon": coordinates[1], "priorities": order,
            })
            assert response.status_code == 200
            result = response.json()
            assert len(result["matches"]) == 10
            assert len({m["position"] for m in result["matches"]}) == 10
            assert label in result["source"]["label"]
            assert result["weights"] == dict(zip(order, [.45, .25, .20, .10]))
            assert result["prioritySource"] == "preset"
            assert result["eligibleCount"] > 10
            assert len(result["query"]) == 25
            weights, criteria = result["weights"], result["criteria"]
            scores = [m["score"] for m in result["matches"]]
            assert scores == sorted(scores)
            for match in result["matches"]:
                assert match["country"]
                explanation = match["explanation"]
                assert explanation["method"] == "exact_interventional_shap_additive_score"
                assert explanation["background_size"] == 10
                reconstructed = explanation["baseline_score"] + math.fsum(f["shap_value"] for f in explanation["features"])
                assert math.isclose(reconstructed, match["score"], rel_tol=1e-8, abs_tol=1e-8)
                assert len(match["values"]) == 25
                expected = (
                    weights["profile"] * (match["error"] / 100) ** 2
                    + weights["range"] * ((match["range"] - criteria["range"]) / 150) ** 2
                    + weights["slope"] * ((match["slope"] - criteria["slope"]) / 2) ** 2
                    + weights["roughness"] * ((match["roughness"] - criteria["roughness"]) / 50) ** 2
                )
                assert math.isclose(expected, match["score"], rel_tol=1e-8, abs_tol=1e-8)
            results.append(result)
    assert results[0]["criteria"] == results[1]["criteria"]
    assert [m["position"] for m in results[0]["matches"]] != [m["position"] for m in results[1]["matches"]]
