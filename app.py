import os
import json
from pathlib import Path
from typing import List, Dict
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import httpx
import uuid
from pydantic import BaseModel, Field, field_validator


# --- конфиг/ключ ---
ORS_API_KEY = os.environ.get("ORS_API_KEY")
if not ORS_API_KEY:
    raise RuntimeError("Не найден ORS_API_KEY в окружении")

BASE_DIR = Path(__file__).parent
BASE_GEO = "https://api.openrouteservice.org/geocode"
BASE_DIRS = "https://api.openrouteservice.org/v2/directions"

# --- приложение ---
app = FastAPI(title="Travel Planner (ORS)")


def pois_path() -> Path:
    return BASE_DIR / "pois.json"

def load_pois() -> list[dict]:
    p = pois_path()
    if not p.exists():
        return []
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

def save_pois(pois: list[dict]) -> None:
    with pois_path().open("w", encoding="utf-8") as f:
        json.dump(pois, f, ensure_ascii=False, indent=2)

class PoiIn(BaseModel):
    name: str = Field(min_length=1)
    lat: float
    lon: float
    tags: list[str] = []

    @field_validator("lat")
    @classmethod
    def _lat(cls, v: float) -> float:
        if not (-90 <= v <= 90):
            raise ValueError("lat must be between -90 and 90")
        return v

    @field_validator("lon")
    @classmethod
    def _lon(cls, v: float) -> float:
        if not (-180 <= v <= 180):
            raise ValueError("lon must be between -180 and 180")
        return v

# если открываешь index.html через этот же бэкенд, CORS можно не включать
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"]
)

# --- статика и корневая страница ---
app.mount("/static", StaticFiles(directory=BASE_DIR / "frontend"), name="static")

@app.get("/")
def root():
    return FileResponse(BASE_DIR / "frontend" / "index.html")

# --- POI из файла ---
@app.get("/pois")
def list_pois() -> List[Dict]:
    path = BASE_DIR / "pois.json"
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


@app.post("/pois", status_code=201)
def create_poi(poi: PoiIn) -> dict:
    pois = load_pois()
    # уникальность имени (без учёта регистра)
    names = {p["name"].strip().lower() for p in pois}
    if poi.name.strip().lower() in names:
        raise HTTPException(409, "POI с таким названием уже существует")

    item = {
        "id": uuid.uuid4().hex,
        "name": poi.name.strip(),
        "lat": poi.lat,
        "lon": poi.lon,
        "tags": poi.tags,
    }
    pois.append(item)
    save_pois(pois)
    return item

@app.delete("/pois/{poi_id}", status_code=204)
def delete_poi(poi_id: str):
    pois = load_pois()
    new_pois = [p for p in pois if p.get("id") != poi_id]
    if len(new_pois) == len(pois):
        raise HTTPException(404, "POI не найден")
    save_pois(new_pois)


# --- геокодер (ORS) ---
@app.get("/geocode")
async def geocode(q: str = Query(..., min_length=2)) -> Dict:
    url = f"{BASE_GEO}/search"
    headers = {"Authorization": ORS_API_KEY}
    params = {"api_key": ORS_API_KEY, "text": q, "size": 5}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, headers=headers, params=params)
    if r.status_code != 200:
        raise HTTPException(r.status_code, f"Geocode error: {r.text}")
    data = r.json()
    out = []
    for f in data.get("features", []):
        geom = f.get("geometry", {})
        props = f.get("properties", {})
        if geom.get("type") == "Point":
            lon, lat = geom.get("coordinates", [None, None])
            out.append({"label": props.get("label") or props.get("name"), "lat": lat, "lon": lon})
    return {"results": out}

# --- маршрут (ORS directions, пешком)---
@app.get("/route")
async def route(from_coord: str, to_coord: str, profile: str = "foot-walking") -> Dict:
    try:
        f_lat, f_lon = [float(x.strip()) for x in from_coord.split(",")]
        t_lat, t_lon = [float(x.strip()) for x in to_coord.split(",")]
    except Exception:
        raise HTTPException(400, "Неверный формат координат. Ожидал 'lat,lon'.")

    url = f"{BASE_DIRS}/{profile}/geojson"
    headers = {"Authorization": ORS_API_KEY, "Content-Type": "application/json"}
    body = {
        "coordinates": [[f_lon, f_lat], [t_lon, t_lat]],  # ORS ждёт lon,lat
        "instructions": False,
        "elevation": False,
        "radiuses": [50, 50],
        "preference": "recommended",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(url, headers=headers, json=body)
    if r.status_code != 200:
        raise HTTPException(r.status_code, f"Directions error: {r.text}")

    data = r.json()
    feat = data.get("features", [])
    if not feat:
        raise HTTPException(502, "Пустой ответ маршрутизатора")
    summary = feat[0]["properties"].get("summary", {})
    return {
        "geojson": data,
        "distance_km": round((summary.get("distance", 0.0)) / 1000, 3),
        "duration_min": round((summary.get("duration", 0.0)) / 60),
        "profile": profile,
    }

# опционально — чтобы работало `python app.py`
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)
