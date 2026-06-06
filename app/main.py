import asyncio
import json
import os
import re
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

import app.env  # noqa: F401
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
    import app.tools.economy  # noqa: F401
    import app.tools.health  # noqa: F401
    import app.tools.mobility  # noqa: F401
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
    mode: Literal["rag", "agent"] = "agent"


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


def format_response_for_chat(text: str) -> str:
    lines = text.splitlines()
    if len(lines) < 4:
        return text

    title_pattern = re.compile(r"^[A-ZÄÖÜ][^:]{2,80}:$")
    blocks: list[tuple[str, list[str]]] = []
    intro_lines: list[str] = []
    index = 0

    while index < len(lines):
        line = lines[index].strip()
        if not line:
            if not blocks:
                intro_lines.append(lines[index])
            index += 1
            continue

        if title_pattern.match(line):
            description: list[str] = []
            index += 1
            while index < len(lines):
                next_line = lines[index].strip()
                if not next_line:
                    break
                if title_pattern.match(next_line):
                    break
                description.append(next_line)
                index += 1

            if description:
                blocks.append((line[:-1], description))
                continue

        if blocks:
            return text

        intro_lines.append(lines[index])
        index += 1

    if len(blocks) < 2:
        return text

    formatted_blocks = [
        f"- **{title}**\n  " + "\n  ".join(description)
        for title, description in blocks
    ]
    intro = "\n".join(intro_lines).strip()
    parts = [part for part in [intro, "\n".join(formatted_blocks)] if part]
    return "\n\n".join(parts)


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


def get_base_context(request: Request) -> dict:
    """Get base context with chatbot config for all pages."""
    return {
        "request": request,
        "llm_configured": llm_is_configured(),
        "rag_configured": rag_is_configured(),
    }


@app.get("/")
async def index(request: Request):
    """Landing page with category overview."""
    from app.data_loader import (
        kiss_population_monthly,
        kiss_students,
        kiss_doctors_pharmacies,
        kiss_employment,
        kiss_tourism_arrivals,
        kiss_schools,
        kiss_library_visits,
        kiss_public_transport,
        cafes_geojson,
    )
    from collections import defaultdict
    from app.tools import get_available_tool_names

    overview = load_json_data("overview")
    environment = load_json_data("environment")
    mobility = load_json_data("mobility")
    living = load_json_data("living")
    economy = load_json_data("economy")
    quality = load_json_data("quality")
    facts = load_json_data("facts")

    # Calculate KPIs from KISS-MD data
    kpis = {
        "population": {"icon": "👥", "value": 240400, "label": "Einwohner"},
        "schools": {"icon": "🏫", "value": 86, "label": "Schulen"},
        "doctors": {"icon": "🏥", "value": 700, "label": "Ärzte & Praxen"},
        "employed": {"icon": "💼", "value": 112000, "label": "Beschäftigte"},
        "tourists": {"icon": "🏨", "value": 451000, "label": "Gäste/Jahr"},
        "students": {"icon": "🎓", "value": 14000, "label": "Studierende"},
        "library_visits": {"icon": "📚", "value": 747000, "label": "Bibliotheksbesuche"},
        "transit": {"icon": "🚌", "value": 41000000, "label": "ÖPNV-Fahrgäste"},
        "cafes": {"icon": "☕", "value": 84, "label": "Cafés"},
    }

    # Get latest population (var5 = total with main residence)
    if kiss_population_monthly:
        latest_pop = kiss_population_monthly[-1]
        if latest_pop.get("var5"):
            kpis["population"]["value"] = latest_pop["var5"]

    # Get schools count
    if kiss_schools:
        latest_year = max(row["var1"] for row in kiss_schools if row.get("var1"))
        schools_count = len([row for row in kiss_schools if row.get("var1") == latest_year])
        kpis["schools"]["value"] = schools_count

    # Get doctors count
    if kiss_doctors_pharmacies:
        by_year = defaultdict(int)
        for row in kiss_doctors_pharmacies:
            if row.get("var1") and row.get("var3"):
                by_year[row["var1"]] += row["var3"]
        if by_year:
            latest_year = max(by_year.keys())
            kpis["doctors"]["value"] = by_year[latest_year]

    # Get employment count (multiply by 2 as data appears to be half - likely one gender/category)
    if kiss_employment:
        by_year = defaultdict(int)
        for row in kiss_employment:
            if row.get("var1") and row.get("var3"):
                by_year[row["var1"]] += row["var3"]
        if by_year:
            latest_year = max(by_year.keys())
            # Data is subdivided by categories - use actual value
            kpis["employed"]["value"] = by_year[latest_year]

    # Get tourism arrivals
    if kiss_tourism_arrivals:
        by_year = defaultdict(int)
        for row in kiss_tourism_arrivals:
            if row.get("var1") and row.get("var3"):
                by_year[row["var1"]] += row["var3"]
        if by_year:
            # Get 2025 data (most recent complete year)
            if 2025 in by_year:
                kpis["tourists"]["value"] = by_year[2025]

    # Get students count (var2 appears to be total students)
    if kiss_students:
        latest = kiss_students[-1]
        if latest.get("var2"):
            kpis["students"]["value"] = latest["var2"]

    # Get library visits
    if kiss_library_visits:
        latest = kiss_library_visits[-1]
        if latest.get("var1"):
            total_visits = sum(
                v for k, v in latest.items()
                if k.startswith("var") and k != "var1" and v is not None
            )
            if total_visits:
                kpis["library_visits"]["value"] = total_visits

    # Get public transport passengers
    if kiss_public_transport:
        latest = kiss_public_transport[-1]
        if latest.get("var2"):
            kpis["transit"]["value"] = latest["var2"]

    # Get cafes/restaurants count
    if cafes_geojson:
        cafe_count = len(cafes_geojson.get("features", []))
        if cafe_count:
            kpis["cafes"]["value"] = cafe_count

    context = {
        **get_base_context(request),
        "overview": overview,
        "environment": environment,
        "mobility": mobility,
        "living": living,
        "economy": economy,
        "quality": quality,
        "facts": facts,
        "kpis": kpis,
        "tools_count": len(get_available_tool_names()),
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
        **get_base_context(request),
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
        **get_base_context(request),
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
        **get_base_context(request),
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
        **get_base_context(request),
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
        **get_base_context(request),
        "quality": quality,
        "facts": quality_facts[:3],
        "breadcrumbs": ["Lebensqualität"],
    }
    return templates.TemplateResponse(request=request, name="quality.html", context=context)


@app.get("/demographics")
async def demographics_page(request: Request):
    """Demographics & Population page."""
    from app.data_loader import kiss_population_monthly

    # Get latest population
    latest_pop = 0
    if kiss_population_monthly:
        latest_row = kiss_population_monthly[-1]
        latest_pop = latest_row.get("var5", 0)  # Total population

    facts = load_json_data("facts")
    pop_facts = [f for f in facts if f.get("category") == "Bevölkerung"]

    context = {
        **get_base_context(request),
        "latest_population": latest_pop,
        "facts": pop_facts[:3],
        "breadcrumbs": ["Demografie"],
    }
    return templates.TemplateResponse(request=request, name="demographics.html", context=context)


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
        return ChatResponse(response=format_response_for_chat(response))

    if payload.mode == "rag":
        response = await asyncio.to_thread(post_rag_chat, messages)
        return ChatResponse(response=format_response_for_chat(response))

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
# KISS-MD data endpoints
# ---------------------------------------------------------------------------


@app.get("/api/data/kiss/population/recent")
async def kiss_population_recent():
    """Get recent population data from KISS-MD (last 5 years)."""
    from app.data_loader import kiss_population_monthly
    from collections import defaultdict

    if not kiss_population_monthly:
        return []

    # Group by year and get December values (year-end population)
    by_year = defaultdict(list)
    for row in kiss_population_monthly:
        if row.get("var1") and row.get("var2") == "Dezember" and row.get("var5"):
            year = row["var1"]
            # var5 appears to be total population (Hauptwohnsitz)
            by_year[year].append(row["var5"])

    # Get last 5 years
    recent_years = sorted(by_year.keys())[-5:]
    return [
        {"year": year, "population": by_year[year][0]}
        for year in recent_years
    ]


@app.get("/api/data/kiss/apprentices")
async def kiss_apprentices_endpoint():
    """Get apprentice statistics from KISS-MD."""
    from app.data_loader import kiss_apprentices

    if not kiss_apprentices:
        return []

    return [
        {
            "year": row["var1"],
            "male": row.get("var2"),
            "female": row.get("var3"),
            "total": row.get("var2", 0) + row.get("var3", 0),
        }
        for row in kiss_apprentices
        if row.get("var1")
    ]


@app.get("/api/data/kiss/gdp")
async def kiss_gdp_endpoint():
    """Get GDP and employment data from KISS-MD."""
    from app.data_loader import kiss_gdp

    if not kiss_gdp:
        return []

    return [
        {
            "year": row["var1"],
            "gdp": row.get("var2"),  # in 1000 EUR
            "gdp_share": row.get("var3"),  # % share
            "employed": row.get("var5"),  # number of employed persons
            "gross_value_added": row.get("var6"),  # in 1000 EUR
        }
        for row in kiss_gdp
        if row.get("var1")
    ]


@app.get("/api/data/kiss/students")
async def kiss_students_endpoint():
    """Get student enrollment data from KISS-MD."""
    from app.data_loader import kiss_students

    if not kiss_students:
        return []

    result = []
    for row in kiss_students:
        if row.get("var1"):
            # Sum all student columns (var2 onwards are different student categories)
            total = sum(v for k, v in row.items() if k.startswith("var") and k != "var1" and v is not None)
            result.append({
                "year": row["var1"],
                "total_students": total,
            })
    return result


@app.get("/api/data/kiss/transport/passengers")
async def kiss_transport_passengers_endpoint():
    """Get public transport passenger data from KISS-MD."""
    from app.data_loader import kiss_public_transport

    if not kiss_public_transport:
        return []

    return [
        {
            "year": row["var1"],
            "passengers": row.get("var2"),  # total passengers transported
        }
        for row in kiss_public_transport
        if row.get("var1") and row.get("var2")
    ]


@app.get("/api/data/kiss/transport/vehicles")
async def kiss_transport_vehicles_endpoint():
    """Get vehicle fleet data from KISS-MD."""
    from app.data_loader import kiss_vehicle_fleet

    if not kiss_vehicle_fleet:
        return []

    return [
        {
            "year": row["var1"],
            "total_vehicles": row.get("var2"),
        }
        for row in kiss_vehicle_fleet
        if row.get("var1") and row.get("var2")
    ]


@app.get("/api/data/kiss/library/visits")
async def kiss_library_visits_endpoint():
    """Get library visit statistics from KISS-MD."""
    from app.data_loader import kiss_library_visits

    if not kiss_library_visits:
        return []

    return [
        {
            "year": row["var1"],
            "total_visits": sum(v for k, v in row.items() if k.startswith("var") and k != "var1" and v is not None),
        }
        for row in kiss_library_visits
        if row.get("var1")
    ]


# ---------------------------------------------------------------------------
# Stabstelle Klima endpoints
# ---------------------------------------------------------------------------


@app.get("/api/data/climate/energy-emissions")
async def climate_energy_emissions_endpoint():
    """Get energy consumption and emissions data from Stabstelle Klima."""
    from app.data_loader import climate_energy_emissions

    return climate_energy_emissions


@app.get("/api/data/climate/led-streetlights")
async def climate_led_streetlights_endpoint():
    """Get LED street lighting conversion data from Stabstelle Klima."""
    from app.data_loader import climate_led_streetlights

    return climate_led_streetlights


@app.get("/api/data/climate/solar-energy")
async def climate_solar_energy_endpoint():
    """Get solar energy generation data from Stabstelle Klima."""
    from app.data_loader import climate_solar_energy

    return climate_solar_energy


# ---------------------------------------------------------------------------
# Demographics endpoints
# ---------------------------------------------------------------------------


@app.get("/api/data/demographics/age-gender")
async def demographics_age_gender_endpoint():
    """Get population by age and gender (latest year)."""
    from app.data_loader import kiss_pop_age_gender

    if not kiss_pop_age_gender:
        return []

    # Get latest year
    latest_year = max(row["var1"] for row in kiss_pop_age_gender if row.get("var1"))
    latest_data = [row for row in kiss_pop_age_gender if row.get("var1") == latest_year]

    return [
        {
            "age": int(row["var2"]) if str(row["var2"]).isdigit() else row["var2"],
            "total": row.get("var3"),
            "male": row.get("var4"),
            "female": row.get("var5"),
        }
        for row in latest_data
        if row.get("var2")
    ]


@app.get("/api/data/demographics/age-groups")
async def demographics_age_groups_endpoint():
    """Get population development by age groups."""
    from app.data_loader import kiss_pop_age_groups

    return kiss_pop_age_groups


@app.get("/api/data/demographics/dependency-ratios")
async def demographics_dependency_ratios_endpoint():
    """Get youth and elderly dependency ratios over time."""
    from app.data_loader import kiss_pop_dependency_ratios

    if not kiss_pop_dependency_ratios:
        return []

    return [
        {
            "year": row["var1"],
            "youth_ratio": row.get("var2"),  # Likely youth dependency
            "elderly_ratio": row.get("var3"),  # Likely elderly dependency
        }
        for row in kiss_pop_dependency_ratios
        if row.get("var1")
    ]


@app.get("/api/data/demographics/foreign-residents")
async def demographics_foreign_residents_endpoint():
    """Get foreign resident population trends."""
    from app.data_loader import kiss_pop_foreign
    from collections import defaultdict

    if not kiss_pop_foreign:
        return []

    # Aggregate by year (data is broken down by district)
    by_year = defaultdict(int)
    for row in kiss_pop_foreign:
        if row.get("var1") and row.get("var3"):
            by_year[row["var1"]] += row["var3"]

    return [
        {
            "year": year,
            "total_foreign": total,
        }
        for year, total in sorted(by_year.items())
    ]


@app.get("/api/data/demographics/migration")
async def demographics_migration_endpoint():
    """Get net migration by age groups."""
    from app.data_loader import kiss_pop_migration

    return kiss_pop_migration


@app.get("/api/data/demographics/districts")
async def demographics_districts_endpoint():
    """Get population by district and gender."""
    from app.data_loader import kiss_pop_districts

    if not kiss_pop_districts:
        return []

    # Get latest year
    latest_year = max(row["var1"] for row in kiss_pop_districts if row.get("var1"))
    latest_data = [row for row in kiss_pop_districts if row.get("var1") == latest_year]

    return latest_data


# ---------------------------------------------------------------------------
# Labor Market endpoints
# ---------------------------------------------------------------------------


@app.get("/api/data/labor/employment")
async def labor_employment_endpoint():
    """Get employment statistics (insured employment at workplace)."""
    from app.data_loader import kiss_employment

    if not kiss_employment:
        return []

    return [
        {
            "year": row["var1"],
            "total_employed": row.get("var2"),
        }
        for row in kiss_employment
        if row.get("var1") and row.get("var2")
    ]


# ---------------------------------------------------------------------------
# Health & Social endpoints
# ---------------------------------------------------------------------------


@app.get("/api/data/health/doctors-pharmacies")
async def health_doctors_pharmacies_endpoint():
    """Get doctors and pharmacies by year."""
    from app.data_loader import kiss_doctors_pharmacies
    from collections import defaultdict

    if not kiss_doctors_pharmacies:
        return []

    # Aggregate by year (data is by district)
    by_year = defaultdict(lambda: {"doctors": 0, "pharmacies": 0})
    for row in kiss_doctors_pharmacies:
        if row.get("var1"):
            year = row["var1"]
            # var3 appears to be doctors, based on sample values
            if row.get("var3"):
                by_year[year]["doctors"] += row["var3"]

    return [
        {
            "year": year,
            "doctors": data["doctors"],
        }
        for year, data in sorted(by_year.items())
    ]


@app.get("/api/data/health/rescue-services")
async def health_rescue_services_endpoint():
    """Get rescue service deployment statistics."""
    from app.data_loader import kiss_rescue_services

    return kiss_rescue_services


# ---------------------------------------------------------------------------
# Construction & Housing endpoints
# ---------------------------------------------------------------------------


@app.get("/api/data/housing/construction-completions")
async def housing_construction_completions_endpoint():
    """Get building construction completions by year."""
    from app.data_loader import kiss_construction_completions

    if not kiss_construction_completions:
        return []

    return [
        {
            "year": row["var1"],
            "total_buildings": row.get("var2"),  # Total completed buildings
        }
        for row in kiss_construction_completions
        if row.get("var1") and row.get("var2")
    ]


# ---------------------------------------------------------------------------
# Education & Culture endpoints (Phase 2)
# ---------------------------------------------------------------------------


@app.get("/api/data/education/schools")
async def education_schools_endpoint():
    """Get schools statistics by year and type."""
    from app.data_loader import kiss_schools
    from collections import Counter, defaultdict

    if not kiss_schools:
        return []

    # Get latest year
    latest_year = max(row["var1"] for row in kiss_schools if row.get("var1"))

    # Count schools by type for latest year
    schools_2023 = [row for row in kiss_schools if row.get("var1") == latest_year]
    types_count = Counter(row.get("var3") for row in schools_2023 if row.get("var3"))

    # Historical school count by year
    by_year = defaultdict(int)
    for row in kiss_schools:
        if row.get("var1"):
            by_year[row["var1"]] += 1

    return {
        "latest_year": latest_year,
        "total_schools": len(schools_2023),
        "by_type": dict(types_count.most_common()),
        "trend": [{"year": year, "total_schools": count} for year, count in sorted(by_year.items())],
    }


# ---------------------------------------------------------------------------
# Tourism & Recreation endpoints (Phase 2)
# ---------------------------------------------------------------------------


@app.get("/api/data/tourism/arrivals")
async def tourism_arrivals_endpoint():
    """Get tourist arrivals by year."""
    from app.data_loader import kiss_tourism_arrivals
    from collections import defaultdict

    if not kiss_tourism_arrivals:
        return []

    # Aggregate monthly data by year
    by_year = defaultdict(lambda: {"total": 0, "domestic": 0, "foreign": 0})
    for row in kiss_tourism_arrivals:
        if row.get("var1") and row.get("var3"):
            year = row["var1"]
            by_year[year]["total"] += row.get("var3", 0) or 0
            by_year[year]["domestic"] += row.get("var4", 0) or 0
            by_year[year]["foreign"] += row.get("var5", 0) or 0

    return [
        {
            "year": year,
            "total_arrivals": data["total"],
            "domestic_arrivals": data["domestic"],
            "foreign_arrivals": data["foreign"],
        }
        for year, data in sorted(by_year.items())
    ]


@app.get("/api/data/tourism/overnight-stays")
async def tourism_overnight_stays_endpoint():
    """Get overnight stays by year."""
    from app.data_loader import kiss_tourism_nights
    from collections import defaultdict

    if not kiss_tourism_nights:
        return []

    # Aggregate monthly data by year
    by_year = defaultdict(lambda: {"total": 0, "domestic": 0, "foreign": 0})
    for row in kiss_tourism_nights:
        if row.get("var1") and row.get("var3"):
            year = row["var1"]
            by_year[year]["total"] += row.get("var3", 0) or 0
            by_year[year]["domestic"] += row.get("var4", 0) or 0
            by_year[year]["foreign"] += row.get("var5", 0) or 0

    return [
        {
            "year": year,
            "total_nights": data["total"],
            "domestic_nights": data["domestic"],
            "foreign_nights": data["foreign"],
        }
        for year, data in sorted(by_year.items())
    ]


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
