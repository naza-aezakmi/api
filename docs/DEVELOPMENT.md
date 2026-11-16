# API development

## Runtime

FastAPI handles request validation, optional custom-task priorities, country labels and explanations. A persistent local Node.js worker reads the elevation atlas and performs the terrain search. The worker does not call the web service.

Use Python 3.12 and Node.js 22. The production Docker image includes both.

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --reload
.venv/bin/pytest -q
```

## Settings

| Variable | Purpose |
|---|---|
| `TERRAIN_ATLAS_PATH` | Override the bundled terrain-atlas directory with a compatible atlas and worker. |
| `OPENAI_API_KEY` | Optional custom-objective priority service. |
| `TERRAIN_AI_MODEL` | Model used by that optional service. |

Without the optional service, custom objectives use the default criterion order. Preset tasks send their priorities directly and need no language-model request. The response reports the priority source.

Cross-origin requests are allowed from `https://nasa.aezakmi.org`. The web application normally calls through its own server routes.

## Search and cache

`POST /terrain/search` accepts Moon latitude −90…90° and longitude −180…180°. Mars longitude can also use 0…360° east. A supplied priorities list must contain each of `profile`, `range`, `slope` and `roughness` exactly once.

The worker caches up to 64 successful results by body, resolved atlas cell and all four weights. Failed searches are not cached. Restarting clears the cache. A new cell still runs the full search.

Country labels use bundled Natural Earth polygons. Unknown labels stay null. SHAP is calculated analytically from the four score penalties against the returned shortlist. [Method and selection rules](https://github.com/naza-aezakmi/ml/blob/main/docs/MODEL_CARD.md).

## Environmental context

Example `POST /terrain/context` request:

```json
{
  "planet": "moon",
  "lat": 0.674,
  "lon": 23.473,
  "earth_lat": 31.701,
  "earth_lon": 59.352
}
```

The response contains separate planetary and Earth passports and `used_in_ranking: false`.

Earth uses NASA POWER climate averages. Mars reads the bundled MCD 6.2 snapshot. Moon reads the relevant Diviner spatial block through HTTP Range, validating status, length and coordinates.

Missing sentinels become null; real zeros are retained. Source failures return an unavailable passport without changing terrain results. Successful point responses are cached in process.

## Experimental Mars lookup

`POST /terrain/analogs` reads the saved ten-type map and Earth catalogue from `app/data/mars`. It uses Python's standard library and needs no scikit-learn at runtime. It is independent of the website's `/terrain/search` flow.

Synchronise experimental and context artifacts from a sibling ML checkout:

```bash
python3 ../ml/scripts/export.py --api .
```

Commit the exported files here. The Docker build does not require a sibling repository. Rebuild country or climate source assets in the ML repository before exporting.

## Deployment

Pushes to `main` run tests, publish a commit-tagged Docker image and deploy to Docker Swarm. See `.github/workflows/deploy.yml` and `docker-stack.yml`.

The existing image namespace is `ghcr.io/org666777148852/nasa-api`, separate from the renamed GitHub organization. The workflow uses the configured `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_KEY` and `DEPLOY_KNOWN_HOSTS` secrets.
