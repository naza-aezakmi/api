import itertools
import math

import pytest

from app.terrain_explain import explain_candidates, feature_penalties


def test_exact_shap_agrees_with_all_feature_permutations():
    criteria = {"range": 90, "slope": 2.4, "roughness": 15}
    weights = {"profile": .2, "range": .1, "slope": .45, "roughness": .25}
    background = [
        {"error": 10, "range": 110, "slope": 2, "roughness": 22},
        {"error": 25, "range": 140, "slope": 3, "roughness": 15},
        {"error": 40, "range": 180, "slope": 5, "roughness": 30},
    ]
    for candidate in background:
        candidate["score"] = math.fsum(feature_penalties(candidate, criteria, weights).values())
    explained = explain_candidates(background, criteria, weights)
    keys = ["error", "range", "slope", "roughness"]
    names = ["profile", "range", "slope", "roughness"]

    def model(row):
        return weights["profile"] * (row["error"] / 100) ** 2 + weights["range"] * ((row["range"] - criteria["range"]) / 150) ** 2 + weights["slope"] * ((row["slope"] - criteria["slope"]) / 2) ** 2 + weights["roughness"] * ((row["roughness"] - criteria["roughness"]) / 50) ** 2

    for candidate in explained:
        expected = dict.fromkeys(keys, 0.0)
        for permutation in itertools.permutations(keys):
            hybrids = [dict(row) for row in background]
            previous = math.fsum(model(row) for row in hybrids) / len(hybrids)
            for key in permutation:
                for row in hybrids:
                    row[key] = candidate[key]
                current = math.fsum(model(row) for row in hybrids) / len(hybrids)
                expected[key] += (current - previous) / math.factorial(4)
                previous = current
        actual = {row["feature"]: row["shap_value"] for row in candidate["explanation"]["features"]}
        for key, name in zip(keys, names, strict=True):
            assert actual[name] == pytest.approx(expected[key], abs=1e-12)
    for feature in names:
        assert math.fsum(next(f["shap_value"] for f in row["explanation"]["features"] if f["feature"] == feature) for row in explained) == pytest.approx(0, abs=1e-12)


def test_explanation_rejects_a_score_that_uses_another_formula():
    with pytest.raises(ValueError, match="does not reconstruct"):
        explain_candidates([{"error": 0, "range": 0, "slope": 0, "roughness": 0, "score": 10}], {"range": 0, "slope": 0, "roughness": 0}, {"profile": .25, "range": .25, "slope": .25, "roughness": .25})
