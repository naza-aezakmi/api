# NASA API

Small FastAPI service for the NASA Moon and Mars explorer.

## Endpoints

- `GET /health` returns `{"status":"ok"}`.
- `GET /docs` shows the generated API documentation.

Cross-origin requests are allowed from `https://nasa.aezakmi.org`.

## Run locally

```sh
python3.12 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --reload
.venv/bin/pytest -q
```

## Deployment

Pushes to `main` run tests, build and publish `ghcr.io/org666777148852/nasa-api`, then deploy the image to Docker Swarm as the `nasa-api` stack. Traefik serves it at `https://api.nasa.aezakmi.org`.

The repository Actions secrets `DEPLOY_HOST`, `DEPLOY_USER`, `DEPLOY_KEY`, and `DEPLOY_KNOWN_HOSTS` provide deployment access.

`POST /terrain/search` accepts a lunar or Martian latitude and longitude and returns
the same ranked Earth analogues as the web atlas. Open `/docs` to try it.
The endpoint forwards requests to the terrain engine bundled in the web service.
For local testing, override `TERRAIN_SEARCH_URL` with
`http://127.0.0.1:3001/api/terrain-search`.
