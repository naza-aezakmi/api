from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, model_validator

from .terrain_engine import engine
from .terrain_priorities import rank_objective, weights_for


router = APIRouter(tags=["Terrain"])
Feature = Literal["profile", "range", "slope", "roughness"]
Latitude = Annotated[float, Field(ge=-90, le=90, strict=True)]
Longitude = Annotated[float, Field(ge=-180, le=360, strict=True)]


class SearchRequest(BaseModel):
    planet: Literal["moon", "mars"] = "moon"
    lat: Latitude
    lon: Longitude
    priorities: list[Feature] | None = Field(default=None, min_length=4, max_length=4)
    objective: str | None = Field(default=None, max_length=600)

    @model_validator(mode="after")
    def validate_search(self):
        if self.planet == "moon" and self.lon > 180:
            raise ValueError("Moon longitude must be between -180 and 180")
        if self.priorities is not None and len(set(self.priorities)) != 4:
            raise ValueError("List all four terrain criteria exactly once")
        return self


class Metrics(BaseModel):
    range: float
    slope: float
    roughness: float


class Candidate(Metrics):
    position: int
    lat: float
    lon: float
    score: float
    error: float
    rotation: int
    values: list[float]
    usa: bool


class TerrainSource(BaseModel):
    label: str
    resolution: float


class ReferenceSource(TerrainSource):
    lat: float
    lon: float


class EarthSource(TerrainSource):
    radius: float


class SearchResult(BaseModel):
    matches: list[Candidate]
    criteria: Metrics
    landCount: int
    eligibleCount: int
    query: list[float]
    step: int
    size: int
    source: ReferenceSource
    earth: EarthSource
    weights: dict[Feature, float]
    prioritySource: Literal["ai", "default", "preset"]


@router.post("/terrain/search", response_model=SearchResult, summary="Find Earth analogues for a lunar or Martian point")
async def search(payload: SearchRequest) -> SearchResult:
    """Compare window-scale elevation grids and return ranked terrestrial analogues."""
    custom = (payload.objective or "").strip()
    order = await rank_objective(custom) if custom else None
    weights = weights_for(order or payload.priorities)
    try:
        result = await engine.search(payload.planet, payload.lat, payload.lon, weights)
        return SearchResult.model_validate({
            **result, "weights": weights,
            "prioritySource": "ai" if order else "default" if custom else "preset",
        })
    except (OSError, RuntimeError, ValueError) as exc:
        raise HTTPException(503, "Terrain search is temporarily unavailable") from exc
