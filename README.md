# NASA API

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
