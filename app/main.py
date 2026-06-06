import asyncio
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from urllib import error, request as urllib_request

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from app.rag_query import answer as rag_answer
from app.rag_query import rag_is_configured


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.data_loader import load_all
    load_all()
    # Import tools to register them
    import app.tools.weather  # noqa: F401
    import app.tools.water_level  # noqa: F401
    import app.tools.air_quality  # noqa: F401
    import app.tools.cafes  # noqa: F401
    import app.tools.trees  # noqa: F401
    import app.tools.accidents  # noqa: F401
    import app.tools.rent  # noqa: F401
    import app.tools.climate  # noqa: F401
    import app.tools.tax  # noqa: F401
    import app.tools.population  # noqa: F401
    import app.tools.transit  # noqa: F401
    import app.tools.rag_tool  # noqa: F401
    yield


app = FastAPI(title="Smart City Dashboard Magdeburg", lifespan=lifespan)

# Mount static files
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

# Add custom template filter for number formatting
def format_number(value):
    """Format number with German thousand separator."""
    try:
        return f"{int(value):,}".replace(",", ".")
    except (ValueError, TypeError):
        return value

templates.env.filters["format_number"] = format_number

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ChatMessage(BaseModel):
    role: str = Field(pattern="^(system|user|assistant)$")
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    mode: Literal["chat", "rag", "agent"] = "agent"


class ChatResponse(BaseModel):
    response: str


# ---------------------------------------------------------------------------
# LLM helpers
# ---------------------------------------------------------------------------


def llm_is_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY") or (os.getenv("SERVER_URL") and os.getenv("SERVER_TOKEN")))


def post_llm_chat(messages: list[dict[str, str]]) -> dict:
    server_url = os.getenv("SERVER_URL")
    server_token = os.getenv("SERVER_TOKEN")

    if not server_url or not server_token:
        raise HTTPException(
            status_code=503,
            detail="LLM backend is not configured. Set SERVER_URL and SERVER_TOKEN.",
        )

    endpoint = f"{server_url.rstrip('/')}/api/llm/chat"
    payload = json.dumps({"messages": messages}).encode("utf-8")
    req = urllib_request.Request(
        endpoint,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {server_token}",
        },
        method="POST",
    )

    try:
        with urllib_request.urlopen(req, timeout=30) as response:
            body = response.read().decode("utf-8")
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise HTTPException(status_code=exc.code, detail=f"LLM backend request failed: {detail}") from exc
    except error.URLError as exc:
        raise HTTPException(status_code=502, detail=f"LLM backend is unreachable: {exc.reason}") from exc

    try:
        parsed = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="LLM backend returned invalid JSON.") from exc

    if "response" not in parsed or not isinstance(parsed["response"], str):
        raise HTTPException(status_code=502, detail="LLM backend returned an unexpected response format.")

    return parsed


def post_rag_chat(messages: list[dict[str, str]]) -> str:
    user_prompt = next(
        (message["content"] for message in reversed(messages) if message["role"] == "user"),
        None,
    )
    if not user_prompt:
        raise HTTPException(status_code=400, detail="No user message provided.")

    try:
        return rag_answer(user_prompt, history=messages)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"RAG backend request failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


def load_json_data(filename: str) -> dict:
    """Load JSON data from static/data directory."""
    data_path = Path(__file__).parent / "static" / "data" / f"{filename}.json"
    try:
        with open(data_path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


@app.get("/")
async def index(request: Request):
    """Landing page with category overview."""
    overview = load_json_data("overview")
    environment = load_json_data("environment")
    mobility = load_json_data("mobility")
    living = load_json_data("living")
    economy = load_json_data("economy")
    quality = load_json_data("quality")
    facts = load_json_data("facts")

    context = {
        "request": request,
        "overview": overview,
        "environment": environment,
        "mobility": mobility,
        "living": living,
        "economy": economy,
        "quality": quality,
        "facts": facts,
    }
    return templates.TemplateResponse(request=request, name="index.html", context=context)


@app.get("/chat")
async def chat_page(request: Request):
    """AI Assistant chat page (formerly dashboard)."""
    from app.data_loader import trees_data, accidents_data, transit_stops, cafes_geojson
    from app.tools import get_available_tool_names

    context = {
        "request": request,
        "title": "KI-Assistent - Smart City Dashboard Magdeburg",
        "llm_configured": llm_is_configured(),
        "rag_configured": rag_is_configured(),
        "tools": get_available_tool_names(),
        "stats": {
            "trees": len(trees_data),
            "accidents": len(accidents_data),
            "transit_stops": len(transit_stops),
            "cafes": len(cafes_geojson.get("features", [])),
        },
        "breadcrumbs": ["KI-Assistent"],
    }
    return templates.TemplateResponse(request=request, name="chat.html", context=context)


@app.get("/environment")
async def environment_page(request: Request):
    """Environment & Climate category page."""
    environment = load_json_data("environment")
    facts = load_json_data("facts")
    env_facts = [f for f in facts if f.get("category") in ["Umwelt", "Klima"]]

    context = {
        "request": request,
        "environment": environment,
        "facts": env_facts[:3],
        "breadcrumbs": ["Umwelt & Klima"],
    }
    return templates.TemplateResponse(request=request, name="environment.html", context=context)


@app.get("/mobility")
async def mobility_page(request: Request):
    """Mobility & Safety category page."""
    mobility = load_json_data("mobility")
    facts = load_json_data("facts")
    mobility_facts = [f for f in facts if f.get("category") == "Mobilität"]

    context = {
        "request": request,
        "mobility": mobility,
        "facts": mobility_facts[:3],
        "breadcrumbs": ["Mobilität & Sicherheit"],
    }
    return templates.TemplateResponse(request=request, name="mobility.html", context=context)


@app.get("/living")
async def living_page(request: Request):
    """Living & Housing category page."""
    living = load_json_data("living")
    facts = load_json_data("facts")
    living_facts = [f for f in facts if f.get("category") == "Wohnen"]

    context = {
        "request": request,
        "living": living,
        "facts": living_facts[:3],
        "breadcrumbs": ["Wohnen & Leben"],
    }
    return templates.TemplateResponse(request=request, name="living.html", context=context)


@app.get("/economy")
async def economy_page(request: Request):
    """Economy & Finance category page."""
    economy = load_json_data("economy")
    facts = load_json_data("facts")
    economy_facts = [f for f in facts if f.get("category") == "Wirtschaft"]

    context = {
        "request": request,
        "economy": economy,
        "facts": economy_facts[:3],
        "breadcrumbs": ["Wirtschaft & Finanzen"],
    }
    return templates.TemplateResponse(request=request, name="economy.html", context=context)


@app.get("/quality")
async def quality_page(request: Request):
    """Quality of Life category page."""
    quality = load_json_data("quality")
    facts = load_json_data("facts")
    quality_facts = [f for f in facts if f.get("category") in ["Kultur", "Bevölkerung"]]

    context = {
        "request": request,
        "quality": quality,
        "facts": quality_facts[:3],
        "breadcrumbs": ["Lebensqualität"],
    }
    return templates.TemplateResponse(request=request, name="quality.html", context=context)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest):
    messages = [message.model_dump() for message in payload.messages[-8:]]

    if payload.mode == "agent":
        from app.agent import run_agent
        user_msg = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
        )
        history = [m for m in messages[:-1] if m["role"] in ("user", "assistant")]
        response = await asyncio.to_thread(run_agent, user_msg, history)
        return ChatResponse(response=response)

    if payload.mode == "rag":
        response = await asyncio.to_thread(post_rag_chat, messages)
        return ChatResponse(response=response)

    response = await asyncio.to_thread(post_llm_chat, messages)
    return ChatResponse(response=response["response"])


# ---------------------------------------------------------------------------
# Data API endpoints
# ---------------------------------------------------------------------------


@app.get("/api/data/trees/summary")
async def trees_summary():
    from app.data_loader import trees_data
    from collections import Counter

    if not trees_data:
        return {"total": 0}

    by_district = Counter(t["stadtteil"] for t in trees_data)
    by_species = Counter(t["gattungsgruppe"] for t in trees_data)
    return {
        "total": len(trees_data),
        "by_district": dict(by_district.most_common(20)),
        "top_species": dict(by_species.most_common(10)),
    }


@app.get("/api/data/accidents/summary")
async def accidents_summary():
    from app.data_loader import accidents_data
    from collections import Counter

    if not accidents_data:
        return {"total": 0}

    by_year = Counter(a["jahr"] for a in accidents_data)
    by_type = {
        "Fahrrad": sum(1 for a in accidents_data if a["ist_rad"]),
        "PKW": sum(1 for a in accidents_data if a["ist_pkw"]),
        "Fußgänger": sum(1 for a in accidents_data if a["ist_fuss"]),
        "Motorrad": sum(1 for a in accidents_data if a["ist_krad"]),
    }
    return {
        "total": len(accidents_data),
        "by_year": dict(sorted(by_year.items())),
        "by_type": by_type,
    }


@app.get("/api/data/climate/yearly")
async def climate_yearly():
    from app.data_loader import climate_monthly

    if not climate_monthly:
        return []

    yearly = {}
    for r in climate_monthly:
        if not r.get("date"):
            continue
        year = r["date"][:4]
        if year not in yearly:
            yearly[year] = {"temps": [], "precip": []}
        if r.get("MO_TT") is not None:
            yearly[year]["temps"].append(r["MO_TT"])
        if r.get("MO_RR") is not None:
            yearly[year]["precip"].append(r["MO_RR"])

    result = []
    for year in sorted(yearly.keys()):
        d = yearly[year]
        if d["temps"]:
            result.append({
                "year": int(year),
                "avg_temp": round(sum(d["temps"]) / len(d["temps"]), 1),
                "total_precip": round(sum(d["precip"])) if d["precip"] else None,
            })
    return result


@app.get("/api/data/rent/by-district")
async def rent_by_district():
    from app.data_loader import mietspiegel_wohnflaeche
    from collections import defaultdict

    data = [r for r in mietspiegel_wohnflaeche if r.get("year") == 2024 and r.get("nettokaltmiete_pro_qm")]
    by_district = defaultdict(list)
    for r in data:
        by_district[r["stadtteil"]].append(r["nettokaltmiete_pro_qm"])

    return [
        {"district": d, "avg_rent": round(sum(v) / len(v), 2)}
        for d, v in sorted(by_district.items(), key=lambda x: sum(x[1]) / len(x[1]), reverse=True)
    ]


@app.get("/api/data/tax/revenue")
async def tax_revenue_endpoint():
    from app.data_loader import tax_revenue

    result = []
    for row in sorted(tax_revenue, key=lambda r: r["jahr"]):
        total = sum(v for k, v in row.items() if k != "jahr" and v is not None)
        result.append({"year": row["jahr"], "total": round(total)})
    return result


@app.get("/api/data/transit/stops")
async def transit_stops_endpoint():
    from app.data_loader import transit_stops
    return transit_stops


@app.get("/api/data/cafes/geojson")
async def cafes_geojson_endpoint():
    from app.data_loader import cafes_geojson
    return cafes_geojson


@app.get("/api/data/districts/geojson")
async def districts_geojson_endpoint():
    from app.data_loader import districts_geojson
    return districts_geojson


@app.get("/api/data/accidents/geojson")
async def accidents_geojson_endpoint():
    from app.data_loader import accidents_data
    features = [
        {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [a["lon"], a["lat"]]},
            "properties": {"jahr": a["jahr"], "kategorie": a["kategorie"], "ist_rad": a["ist_rad"]},
        }
        for a in accidents_data
        if a.get("lon") and a.get("lat")
    ]
    return {"type": "FeatureCollection", "features": features}


# ---------------------------------------------------------------------------
# Live data proxy endpoints
# ---------------------------------------------------------------------------


@app.get("/api/live/weather")
async def live_weather():
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            "https://api.brightsky.dev/current_weather",
            params={"lat": 52.1205, "lon": 11.6276},
        )
        r.raise_for_status()
        return r.json()


@app.get("/api/live/water-level")
async def live_water_level():
    station = "MAGDEBURG-STROMBR%C3%9CCKE"
    base = "https://www.pegelonline.wsv.de/webservices/rest-api/v2"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{base}/stations/{station}/W/currentmeasurement.json")
        r.raise_for_status()
        return r.json()


@app.get("/api/live/air-quality")
async def live_air_quality():
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get("https://data.sensor.community/airrohr/v1/filter/area=52.1205,11.6276,10")
        r.raise_for_status()
        data = r.json()

    pm10 = []
    pm25 = []
    for sensor in data:
        for sv in sensor.get("sensordatavalues", []):
            try:
                val = float(sv["value"])
                if sv["value_type"] == "P1":
                    pm10.append(val)
                elif sv["value_type"] == "P2":
                    pm25.append(val)
            except (ValueError, KeyError):
                continue

    return {
        "pm10": round(sum(pm10) / len(pm10), 1) if pm10 else None,
        "pm25": round(sum(pm25) / len(pm25), 1) if pm25 else None,
        "sensors": len(pm10),
    }
