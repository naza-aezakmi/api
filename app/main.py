from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .terrain_search import router as terrain_search
from .mars_analogs import router as mars_analogs
from .environment import router as environment


app = FastAPI(title="NASA API", docs_url="/docs")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://nasa.aezakmi.org"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


app.include_router(terrain_search)
app.include_router(mars_analogs)
app.include_router(environment)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
