"""Physical checks using a known plane and a known residual, not a copy of the score."""
import json
import math
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('terrain-atlas/relief-worker.js', 'utf8').replace('importScripts("relief-codec.js");', '');
const sandbox = { fetch: async () => ({ok: true, json: async () => ({})}), self: {}, api: {} };
vm.runInNewContext(source + '\napi.stats = terrainStats;', sandbox);
console.log(JSON.stringify(sandbox.api.stats(JSON.parse(fs.readFileSync(0, 'utf8')), 1)));
"""


def stats(values):
    result = subprocess.run(["node", "-e", SCRIPT], input=json.dumps(values), text=True, capture_output=True, cwd=ROOT, check=True)
    return json.loads(result.stdout)


def plane():
    # An exact z = 500 + 0.004*x + 0.006*y metre plane on a 10 km square.
    return [500 + .004 * x + .006 * y for y in [5000, 2500, 0, -2500, -5000] for x in [-5000, -2500, 0, 2500, 5000]]


def test_known_plane_has_correct_grade_and_zero_roughness():
    result = stats(plane())
    assert result["slope"] == pytest.approx(math.degrees(math.atan(math.hypot(.004, .006))))
    assert result["roughness"] == pytest.approx(0, abs=1e-8)
    assert result["mean"] == 500
    assert result["range"] == 100


def test_center_obstacle_survives_plane_detrending():
    values = plane()
    values[12] += 25
    result = stats(values)
    assert result["slope"] == pytest.approx(math.degrees(math.atan(math.hypot(.004, .006))))
    # The fitted mean rises by 1 m: residuals are +24 at centre and -1 elsewhere.
    assert result["roughness"] == pytest.approx(math.sqrt(24), abs=1e-8)
