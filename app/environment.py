"""Contextual environmental passports. These values never enter terrain scores."""
import asyncio
import json
import math
from functools import lru_cache
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Annotated, Literal

router = APIRouter(prefix="/terrain", tags=["Environmental context"])
PDS_BASE = "https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/data_derived_gcp/"
POWER_BASE = "https://power.larc.nasa.gov/api/temporal/climatology/point"
MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"]


class ContextRequest(BaseModel):
    planet: Literal["moon", "mars"]
    lat: Annotated[float, Field(ge=-90, le=90, allow_inf_nan=False, strict=True)]
    lon: Annotated[float, Field(ge=-180, le=360, allow_inf_nan=False, strict=True)]
    earth_lat: Annotated[float, Field(ge=-90, le=90, allow_inf_nan=False, strict=True)]
    earth_lon: Annotated[float, Field(ge=-180, le=180, allow_inf_nan=False, strict=True)]


def metric(key, label, value, unit, description):
    return {"id": key, "label": label, "value": value, "unit": unit, "description": description}


def read_url(url, *, headers=None, limit=512_000):
    request = Request(url, headers={"User-Agent": "NASA-Analog-Explorer/1.0 (nasa.aezakmi.org)", **(headers or {})})
    with urlopen(request, timeout=14) as response:
        if headers and "Range" in headers:
            requested = headers["Range"].removeprefix("bytes=")
            if response.status != 206 or not response.headers.get("Content-Range", "").startswith("bytes " + requested + "/"):
                raise ValueError("PDS did not honor the requested byte range")
        data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError("Environment response too large")
        return data


def valid_number(value, fill=-999):
    return isinstance(value, (int, float)) and math.isfinite(value) and value != fill


@lru_cache(maxsize=256)
def earth_passport(lat, lon):
    url = POWER_BASE + "?" + urlencode({"parameters": "T2M,TS,PRECTOTCORR,RH2M,WS10M,PS", "community": "RE", "latitude": lat, "longitude": lon, "format": "JSON"})
    data = json.loads(read_url(url))
    parameters, header = data["properties"]["parameter"], data["header"]
    fill = header.get("fill_value", -999)

    def annual(key, factor=1):
        value = parameters.get(key, {}).get("ANN")
        return round(value * factor, 3) if valid_number(value, fill) else None

    monthly = [parameters.get("T2M", {}).get(m) for m in MONTHS]
    valid_months = [v for v in monthly if valid_number(v, fill)]
    metrics = [
        metric("air_temperature_2m_c", "Air temperature · 2 m", annual("T2M"), "°C", "Annual climatological mean air temperature, 2 m above the surface."),
        metric("surface_temperature_c", "Surface temperature", annual("TS"), "°C", "Annual climatological mean Earth skin temperature; different from air temperature."),
        metric("coldest_month_c", "Coldest mean month", min(valid_months) if len(valid_months) == 12 else None, "°C", "Minimum of twelve monthly mean air temperatures, not a daily extreme."),
        metric("warmest_month_c", "Warmest mean month", max(valid_months) if len(valid_months) == 12 else None, "°C", "Maximum of twelve monthly mean air temperatures, not a daily extreme."),
        metric("relative_humidity_pct", "Relative humidity · 2 m", annual("RH2M"), "%", "Annual climatological mean relative humidity, 2 m above the surface."),
        metric("precipitation_mm_day", "Precipitation", annual("PRECTOTCORR"), "mm/day", "Climatological mean daily precipitation; not the current forecast."),
        metric("wind_10m_m_s", "Wind speed · 10 m", annual("WS10M"), "m/s", "Annual climatological mean wind speed at 10 m."),
        metric("pressure_pa", "Surface pressure", annual("PS", 1000), "Pa", "Annual climatological mean pressure; NASA POWER kPa converted to Pa."),
    ]
    return {"body": "earth", "status": "available" if all(m["value"] is not None for m in metrics) else "partial", "metrics": metrics,
            "source": {"label": "NASA POWER · MERRA-2", "url": url, "period": header.get("range", "Climatological monthly and annual means")},
            "sampled_location": {"lat": lat, "lon": lon, "note": "Point request sampled from the native POWER meteorological grid; not a site weather station."},
            "notes": ["Climate norms describe typical conditions over the source period, not current weather or temperatures at individual rocks."]}


@lru_cache(maxsize=1)
def mars_grid():
    return json.loads((Path(__file__).parent / "data/environment/mars_climate.json").read_text())


def mars_passport(lat, lon):
    c = mars_grid()
    wrap = lambda x: (x + 180) % 360 - 180
    y = min(range(len(c["latitudes"])), key=lambda i: abs(c["latitudes"][i] - lat))
    x = min(range(len(c["longitudes"])), key=lambda i: abs(wrap(c["longitudes"][i] - lon)))
    values = {name: field[y][x] for name, field in c["fields"].items()}
    return {"body": "mars", "status": "available", "metrics": [
        metric("surface_temperature_c", "Surface temperature", values["surface_temperature_c"], "°C", "Modeled surface temperature at this season and local solar time."),
        metric("air_temperature_10m_c", "Air temperature · 10 m", values["air_temperature_10m_c"], "°C", "Modeled atmospheric temperature at 10 m; Earth air values are measured at 2 m."),
        metric("pressure_pa", "Pressure · 10 m", values["pressure_10m_pa"], "Pa", "Modeled atmospheric pressure at 10 m."),
        metric("wind_10m_m_s", "Wind speed · 10 m", values["wind_10m_m_s"], "m/s", "Modeled atmospheric wind speed at 10 m."),
        metric("relative_humidity_pct", "Relative humidity", None, "%", "Not obtained from this model snapshot; missing is not zero."),
        metric("precipitation_mm_day", "Precipitation", None, "mm/day", "Not obtained from this model snapshot; missing is not zero."),
    ], "source": {"label": "Mars Climate Database 6.2", "url": "https://www-mars.lmd.jussieu.fr/", "period": "Ls = 0°, local solar noon; average solar climatology scenario"},
        "sampled_location": {"lat": c["latitudes"][y], "lon": c["longitudes"][x], "note": "Nearest coarse MCD model node, not an observation at the clicked coordinate."},
        "notes": ["One modeled season and local time, not current weather or a Martian annual mean.", "Earth annual climatology and this Mars snapshot describe different periods and heights; direct climate equivalence is not claimed."]}


def moon_cell(lat, lon):
    # GCP tables: 10-degree latitude bands; longitude-major, then latitude,
    # then 96 quarter-hour bins. Every fixed-length record is 113 bytes.
    lon = (lon + 180) % 360 - 180
    band = min(17, math.floor((lat + 90) / 10))
    south = -90 + band * 10
    row = min(19, math.floor((lat - south) * 2))
    col = min(719, math.floor((lon + 180) * 2))
    return south, row, col


def band_name(latitude):
    return f"{abs(latitude):02d}{'n' if latitude >= 0 else 's'}"


@lru_cache(maxsize=128)
def moon_cell_passport(south, row, col):
    north = south + 10
    # The zero in the 10s..0 band is denoted 00s in the PDS filename.
    upper = "00s" if north == 0 else band_name(north)
    url = PDS_BASE + f"global_cumul_avg_cyl_{band_name(south)}{upper}_002.tab"
    cell_index = col * 20 + row
    start, size = 113 + cell_index * 96 * 113, 96 * 113
    data = read_url(url, headers={"Range": f"bytes={start}-{start + size - 1}"}, limit=size)
    if len(data) != size:
        raise ValueError("Incomplete Diviner cell")
    sampled_lat, sampled_lon = south + row * .5 + .25, -180 + col * .5 + .25
    temperatures = []
    for line in data.decode("ascii").splitlines():
        values = [float(value) for value in line.split(",")]
        if len(values) != 11 or abs(values[0] - sampled_lon) > .001 or abs(values[1] - sampled_lat) > .001:
            raise ValueError("Diviner coordinates do not match byte indexing")
        tbol = values[-1]
        if 0 < tbol < 500 and math.isfinite(tbol):
            temperatures.append(tbol - 273.15)
    low, high = (min(temperatures), max(temperatures)) if temperatures else (None, None)
    return {"body": "moon", "status": "available" if len(temperatures) == 96 else "partial", "metrics": [
        metric("surface_temperature_min_c", "Cold surface · observed bins", round(low, 1) if low is not None else None, "°C", "Minimum across available local-time mean bolometric temperatures; not a resolved cold-trap extreme."),
        metric("surface_temperature_max_c", "Hot surface · observed bins", round(high, 1) if high is not None else None, "°C", "Maximum across available local-time mean bolometric temperatures; not a current reading."),
        metric("surface_temperature_span_c", "Observed thermal span", round(high - low, 1) if low is not None else None, "°C", "Difference between available hot and cold local-time averages."),
    ], "source": {"label": "NASA LRO Diviner · Global Cumulative Product", "url": PDS_BASE, "data_url": url, "period": "Observations 5 Jul 2009 – 1 Apr 2015; 0.25-hour lunar local-time bins"},
        "sampled_location": {"lat": sampled_lat, "lon": sampled_lon, "note": "0.5° spatial bin; lunar local solar time spans a lunar day, not 24 Earth hours."},
        "coverage": {"valid_bins": len(temperatures), "total_bins": 96},
        "notes": ["Air temperature, rain, humidity and ordinary atmospheric wind are not applicable to the lunar surface.", "Missing observation bins may omit the hottest or coldest local time. Small shadowed craters are not resolved by this global bin.", "These surface radiometric temperatures are not equivalent to Earth's annual air-temperature climatology."]}


def unavailable(body, reason):
    return {"body": body, "status": "unavailable", "metrics": [], "source": None, "sampled_location": None, "notes": [reason]}


def safe_passport(body, lat, lon):
    try:
        if body == "earth":
            return earth_passport(round(lat, 4), round(lon, 4))
        if body == "mars":
            return mars_passport(lat, lon)
        return moon_cell_passport(*moon_cell(lat, lon))
    except (OSError, HTTPError, URLError, TimeoutError, ValueError, KeyError, TypeError):
        return unavailable(body, "The environmental data source is temporarily unavailable or has no valid data here. Terrain search is still available; retry the passport later.")


@router.post("/context", summary="Get separate environmental passports without changing terrain ranking")
async def context(payload: ContextRequest) -> dict:
    reference, earth = await asyncio.gather(
        asyncio.to_thread(safe_passport, payload.planet, payload.lat, payload.lon),
        asyncio.to_thread(safe_passport, "earth", payload.earth_lat, payload.earth_lon),
    )
    return {"reference": reference, "earth": earth, "used_in_ranking": False,
            "comparison_note": "Passports describe different periods, heights and physical quantities. They help plan tests but are not an environmental similarity score."}
