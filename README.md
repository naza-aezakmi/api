# Terrain search API

The service behind the [Moon and Mars explorer](https://nasa.aezakmi.org). It finds Earth terrain similar to a selected planetary location and explains the comparison.

**[Interactive API docs](https://api.nasa.aezakmi.org/docs) · [Presentation (PDF)](https://github.com/naza-aezakmi/.github/blob/main/profile/presentation.pdf) · [Method](https://github.com/naza-aezakmi/ml/blob/main/docs/MODEL_CARD.md) · [Data sources](https://github.com/naza-aezakmi/ml/blob/main/docs/DATA_SOURCES.md)**

## What it does

The search reads a **10 × 10 km** terrain window from the Moon or Mars atlas and compares it with **1,356,072 eligible Earth windows**.

It uses four criteria: aligned elevation profile, elevation range, fitted-plane slope and residual roughness. The testing task sets their weights. Lower scores mean less terrain mismatch.

The response contains ten candidates with coordinates, countries, terrain measurements and exact SHAP explanations. A separate endpoint supplies environmental conditions; these do not change the ranking.

## Endpoints

| Endpoint | Purpose |
|---|---|
| `POST /terrain/search` | Moon/Mars-to-Earth terrain search used by the website. |
| `POST /terrain/context` | Earth and planetary environmental passports, with sources and coverage. |
| `POST /terrain/analogs` | Separate experimental Mars lookup: ten trained terrain types and a fixed Earth catalogue. |
| `GET /health` | Service health. |
| `GET /docs` | Request and response schemas. |

Example search for Jezero, prioritising rover-testing criteria:

```json
{
  "planet": "mars",
  "lat": 18.44,
  "lon": 77.45,
  "priorities": ["slope", "roughness", "profile", "range"]
}
```

The shortlist includes a geographic allocation rule. It is a set of recommendations, rather than an unconditional global top ten. [Selection and score details](https://github.com/naza-aezakmi/ml/blob/main/docs/MODEL_CARD.md).

## Run locally

Requires **Python 3.12** and **Node.js 22**.

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs`. Run checks with `.venv/bin/pytest -q`.

Built with **FastAPI**, a persistent **Node.js** terrain worker and a bundled elevation atlas. [Development notes](docs/DEVELOPMENT.md) cover configuration, caching and deployment.

This is regional site screening. The service does not predict rover passability or replace detailed DEM and field checks.
