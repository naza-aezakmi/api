# NASA API

The production website uses `POST /terrain/search` for **both Moon and Mars**. It returns ten Earth candidates per point and study objective, using the same four weighted criteria: aligned elevation profile, elevation range, mean slope and RMS roughness. The existing field screen and geographic shortlist rules apply to both bodies. `/terrain/analogs` below is a separate experimental prototype catalog and is not used by the current website flow.

## Country labels, exact SHAP and environmental passports

Each `/terrain/search` candidate now includes `country`, `country_code` and `explanation`. Labels are determined offline from bundled Natural Earth 1:50m country polygons; an unresolved point stays null rather than being assigned an invented country. Antarctica is a geographic label, not a sovereign-state assertion.

The explanation uses exact interventional SHAP of the additive mismatch score. For matching descriptor j, `phi_j = penalty_j(candidate) − mean_shortlist(penalty_j)`. The baseline is the **mean score of the returned ten places**, not the entire Earth or a training population. Baseline plus all four attributions reconstructs the ranking score. Negative attribution reduces mismatch relative to that baseline; positive increases it. This explains terrain scoring, while water screening and geographic allocation remain separate selection rules. Tests independently compare all 24 feature permutations with the analytical result. No approximate explainer or extra inference service is needed.

The plane-gradient normalization was corrected to sum x²/y² over **all 25 samples**: 312,500,000 m² for the 2.5 km spacing. The previous constant was half that sum, overestimated gradients and could clamp genuine residual roughness to zero. Known-plane and known-residual tests validate the physical values. This correction can reorder candidates; contextual climate still has no effect on ranking.

`POST /terrain/context` accepts source and Earth coordinates:

```json
{"planet":"moon","lat":0.674,"lon":23.473,"earth_lat":31.701,"earth_lon":59.352}
```

It returns two separate passports and `used_in_ranking: false`. The user explicitly selected contextual climate, so these values **do not change ranking**:

- Earth: NASA POWER / MERRA-2 annual air and skin temperature, coldest/warmest monthly mean air temperature, relative humidity, precipitation, wind at 10 m and surface pressure. The source's actual climatological period is preserved; kPa are converted to Pa. Missing sentinels become null; a real zero is retained.
- Mars: the bundled MCD 6.2 coarse snapshot at Ls=0°, local solar noon, average solar scenario; surface temperature and atmospheric temperature/pressure/wind at 10 m. Humidity and precipitation are unavailable, not zero.
- Moon: NASA LRO Diviner Global Cumulative Product, 2009-07-05…2015-04-01. A 0.5° spatial bin contains 96 quarter-hour lunar local-time mean bolometric temperatures. Range requests fetch only that bin's 10,848 bytes from the PDS table. The reader validates 206/Content-Range, length and row coordinates before using data. The passport reports min/max/span across available observations plus valid-bin coverage; missing local-time bins and unresolved shadowed craters limit the range. Lunar local time does not mean a 24-Earth-hour day.

Earth climate norms, a Mars model snapshot and lunar surface radiometry differ in period, height and physical quantity. The passports show those differences and never claim environmental equivalence. Source failures return an unavailable passport without affecting terrain results. Successful point responses are cached in process; failed upstream calls can be retried. The web loads conditions separately so the ten search results appear first.

Context artifacts live in the ML repository under `artifacts/environment`; `python3 ../ml/scripts/export.py --api .` synchronizes them. Rebuild country data with `ml/scripts/build_country_index.py` and the Mars snapshot with `ml/scripts/export_context_data.py`. Runtime uses Python's standard library only.

## Mars ML analog lookup

`POST /terrain/analogs` returns the trained terrain type, three named Earth candidates, feature-by-feature evidence, and separate climate context for a Mars coordinate:

```json
{"planet":"mars","lat":18.44,"lon":77.45}
```

Latitudes are −90…90°; longitudes −180…360° east (normalized in the response). Unsupported planets and invalid coordinates return 422. The complete global 0.5° type map and catalog are bundled under `app/data/mars`, already included by `COPY app ./app` in the Dockerfile. Inference uses Python's standard library; no model server, external service, sklearn, or key is required. The existing `/terrain/search` flow is unchanged.

The release comes from the sibling `ml` repository: run `python3 ../ml/scripts/export.py --api .` and commit the exported data and `app/mars_lookup.py`. Run `pytest -q` under Python 3.12 / Node 22 before deployment. The experimental browser bundle can be used independently of this endpoint; it is not the website's current search path.

The model explains regional terrain similarity, not soil composition, climate equivalence, or rover passability. Every coordinate in one of the ten classes shares its Earth catalog. Read the ML repository's model card before interpreting results.

**[Explorer](https://nasa.aezakmi.org)** · **[Interactive API docs](https://api.nasa.aezakmi.org/docs)** · **[Health check](https://api.nasa.aezakmi.org/health)**

FastAPI service for the [Moon and Mars explorer](https://github.com/Org666777148852/web). It owns the terrain data, search worker, request validation, and optional AI priority ranking. The web app only forwards search requests here.

## Endpoints

- `GET /health` returns `{"status":"ok"}`.
- `GET /docs` shows the generated API documentation.
- `POST /terrain/search` ranks Earth terrain analogues for a Moon or Mars location.

Cross-origin requests are allowed from `https://nasa.aezakmi.org`.

## Run locally

```sh
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --reload
.venv/bin/pytest -q
```

Node.js 22 is also required to run the bundled relief worker. The production image includes it.

## Deployment

Pushes to `main` run tests, build and publish `ghcr.io/org666777148852/nasa-api`, then deploy the image to Docker Swarm as the `nasa-api` stack. Traefik serves it at `https://api.nasa.aezakmi.org`.

The repository Actions secrets `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_KEY`, and `DEPLOY_KNOWN_HOSTS` provide deployment access.

`POST /terrain/search` accepts a lunar or Martian latitude and longitude and returns
ranked Earth analogues. The API owns the Atlas relief data and runs its worker in a
persistent local Node.js process. It does not call the web service. Node.js 22 is
required for local development; the production image includes it. Set
`TERRAIN_ATLAS_PATH` to use another compatible relief index.

Set `OPENAI_API_KEY` and `TERRAIN_AI_MODEL` on this service to rank priorities for
custom objectives. Without them, the API uses the default priorities.
