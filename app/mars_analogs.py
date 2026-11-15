"""Mars ML analog catalog, independent from the existing detailed terrain search."""
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter
from pydantic import BaseModel, Field

from .mars_lookup import lookup_mars

router = APIRouter(prefix="/terrain", tags=["Mars ML analogs"])
DATA = Path(__file__).resolve().parent / "data/mars"


class AnalogRequest(BaseModel):
    planet: Literal["mars"] = "mars"
    lat: Annotated[float, Field(ge=-90, le=90, strict=True, allow_inf_nan=False)]
    lon: Annotated[float, Field(ge=-180, le=360, strict=True, allow_inf_nan=False)]


@router.post("/analogs", summary="Find Earth analogs for a Mars coordinate from the trained terrain map")
def analogs(request: AnalogRequest) -> dict:
    return lookup_mars(request.lat, request.lon, DATA)
