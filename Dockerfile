FROM node:22-bookworm-slim AS node

FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/Org666777148852/api"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=node /usr/local/bin/node /usr/local/bin/node
RUN apt-get update && apt-get install -y --no-install-recommends libstdc++6 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 10001 app

COPY --chown=app:app app ./app
COPY --chown=app:app terrain-atlas ./terrain-atlas
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=3)'

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
