"""Real atlas regression: caching must preserve body, weights and coordinates."""
import json
from pathlib import Path
import subprocess

import pytest

from app.terrain_explain import feature_penalties
from app.terrain_priorities import weights_for


def test_worker_repeated_cell_alias_and_changed_objective():
    weights = weights_for(['slope', 'roughness', 'profile', 'range'])
    alternate = weights_for(['profile', 'range', 'slope', 'roughness'])
    requests = [
        dict(planet='mars', lat=18.65, lon=-133.8, weights=weights),
        dict(planet='mars', lat=18.65, lon=-133.8, weights=alternate),
        dict(planet='moon', lat=18.65, lon=-133.8, weights=weights),
        dict(planet='mars', lat=18.65, lon=226.2, weights=weights),
        dict(planet='mars', lat=18.65, lon=-133.8, weights=weights),
    ]
    process = subprocess.run(
        ['node', 'app/terrain_engine.cjs'],
        input=''.join(json.dumps(request) + '\n' for request in requests),
        text=True, capture_output=True, cwd=Path(__file__).resolve().parents[1],
        check=True, timeout=60,
    )
    results = [json.loads(line) for line in process.stdout.splitlines()]
    assert len(results) == len(requests)
    assert all(result['kind'] == 'results' for result in results)
    assert results[0] == results[3] == results[4]
    assert results[0]['source']['label'] != results[2]['source']['label']
    assert results[0]['matches'] != results[1]['matches']
    for request, result in zip(requests, results, strict=True):
        for candidate in result['matches']:
            score = sum(feature_penalties(candidate, result['criteria'], request['weights']).values())
            assert candidate['score'] == pytest.approx(score, abs=1e-8)
