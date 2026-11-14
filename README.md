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
