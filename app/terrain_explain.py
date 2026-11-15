"""Exact interventional SHAP for the additive terrain-distance score.

Background is the returned shortlist, not the global land population. Each of the
four score terms depends on only one matching descriptor, so phi_j = g_j(x_j) -
mean_background(g_j). Geography/land masks are selection rules outside this score.
"""
from math import fsum, isclose

NORMALIZATIONS = {"profile": 100.0, "range": 150.0, "slope": 2.0, "roughness": 50.0}


def feature_penalties(candidate, criteria, weights):
    differences = {"profile": candidate["error"], **{key: candidate[key] - criteria[key] for key in ("range", "slope", "roughness")}}
    return {key: weights[key] * (differences[key] / scale) ** 2 for key, scale in NORMALIZATIONS.items()}


def explain_candidates(candidates, criteria, weights):
    if not candidates:
        return []
    penalties = [feature_penalties(candidate, criteria, weights) for candidate in candidates]
    means = {key: fsum(row[key] for row in penalties) / len(penalties) for key in NORMALIZATIONS}
    baseline = fsum(means.values())
    results = []
    for candidate, row in zip(candidates, penalties, strict=True):
        score = fsum(row.values())
        if not isclose(score, candidate["score"], rel_tol=1e-8, abs_tol=1e-8):
            raise ValueError("Terrain explanation does not reconstruct the ranking score")
        features = [{"feature": key, "weight": weights[key], "penalty": row[key], "baseline_penalty": means[key], "shap_value": row[key] - means[key]} for key in NORMALIZATIONS]
        results.append({**candidate, "explanation": {
            "method": "exact_interventional_shap_additive_score",
            "background": "mean of the returned shortlist", "background_size": len(candidates),
            "baseline_score": baseline, "score": candidate["score"], "features": features,
        }})
    return results
