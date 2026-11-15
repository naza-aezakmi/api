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
ranked Earth analogues. The API owns the Atlas relief data and runs its worker in a
persistent local Node.js process. It does not call the web service. Node.js 22 is
required for local development; the production image includes it. Set
`TERRAIN_ATLAS_PATH` to use another compatible relief index.

Set `OPENAI_API_KEY` and `TERRAIN_AI_MODEL` on this service to rank priorities for
custom objectives. Without them, the API uses the default priorities.
