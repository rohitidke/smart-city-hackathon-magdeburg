"""Data processor for Smart City Dashboard - aggregates all datasets into dashboard-ready JSON."""

import json
from pathlib import Path
from collections import Counter, defaultdict
from typing import Any


def process_all_data() -> dict[str, Any]:
    """Process all datasets and return aggregated dashboard data."""
    from app.data_loader import (
        trees_data,
        accidents_data,
        climate_monthly,
        mietspiegel_wohnflaeche,
        tax_revenue,
        transit_stops,
        cafes_geojson,
        districts_geojson,
    )

    # Overview KPIs
    overview = {
        "kpis": {
            "trees": {"value": len(trees_data), "label": "Straßenbäume", "icon": "🌳"},
            "accidents": {"value": len(accidents_data), "label": "Unfälle (2016-2023)", "icon": "🚦"},
            "transit_stops": {"value": len(transit_stops), "label": "Haltestellen", "icon": "🚌"},
            "cafes": {"value": len(cafes_geojson.get("features", [])), "label": "Cafés & Restaurants", "icon": "☕"},
        },
        "last_updated": "2024-06-06",
    }

    # Environment data
    environment = process_environment_data(trees_data, climate_monthly)

    # Mobility data
    mobility = process_mobility_data(accidents_data, transit_stops)

    # Living data
    living = process_living_data(mietspiegel_wohnflaeche, districts_geojson)

    # Economy data
    economy = process_economy_data(tax_revenue)

    # Quality of life data
    quality = process_quality_data(cafes_geojson)

    # Fun facts
    facts = generate_facts(trees_data, accidents_data, climate_monthly, mietspiegel_wohnflaeche, tax_revenue)

    return {
        "overview": overview,
        "environment": environment,
        "mobility": mobility,
        "living": living,
        "economy": economy,
        "quality": quality,
        "facts": facts,
    }


def process_environment_data(trees_data: list, climate_monthly: list) -> dict:
    """Process environment-related data."""
    if not trees_data:
        return {"total_trees": 0}

    # Tree statistics
    by_district = Counter(t.get("stadtteil", "Unbekannt") for t in trees_data)
    by_species = Counter(t.get("gattungsgruppe", "Unbekannt") for t in trees_data)

    # Climate statistics
    climate_years = {}
    if climate_monthly:
        for record in climate_monthly:
            if not record.get("date"):
                continue
            year = record["date"][:4]
            if year not in climate_years:
                climate_years[year] = {"temps": [], "precip": []}
            if record.get("MO_TT") is not None:
                climate_years[year]["temps"].append(record["MO_TT"])
            if record.get("MO_RR") is not None:
                climate_years[year]["precip"].append(record["MO_RR"])

    climate_trend = []
    for year in sorted(climate_years.keys()):
        d = climate_years[year]
        if d["temps"]:
            avg_temp = sum(d["temps"]) / len(d["temps"])
            total_precip = sum(d["precip"]) if d["precip"] else 0
            climate_trend.append({
                "year": int(year),
                "avg_temp": round(avg_temp, 1),
                "total_precip": round(total_precip, 1),
            })

    return {
        "total_trees": len(trees_data),
        "top_species": dict(by_species.most_common(10)),
        "trees_by_district": dict(by_district.most_common(10)),
        "climate_trend": climate_trend[-35:] if climate_trend else [],  # Last 35 years
        "insight": generate_climate_insight(climate_trend) if climate_trend else "",
    }


def process_mobility_data(accidents_data: list, transit_stops: list) -> dict:
    """Process mobility and safety data."""
    if not accidents_data:
        return {"total_accidents": 0}

    by_year = Counter(a.get("jahr") for a in accidents_data if a.get("jahr"))
    by_type = {
        "Fahrrad": sum(1 for a in accidents_data if a.get("ist_rad")),
        "PKW": sum(1 for a in accidents_data if a.get("ist_pkw")),
        "Fußgänger": sum(1 for a in accidents_data if a.get("ist_fuss")),
        "Motorrad": sum(1 for a in accidents_data if a.get("ist_krad")),
    }

    return {
        "total_accidents": len(accidents_data),
        "accidents_by_year": dict(sorted(by_year.items())),
        "accidents_by_type": by_type,
        "transit_stops": len(transit_stops),
        "insight": generate_accident_insight(by_year, by_type),
    }


def process_living_data(mietspiegel_data: list, districts_geojson: dict) -> dict:
    """Process living and housing data."""
    if not mietspiegel_data:
        return {"districts": 0}

    # 2024 rent data by district
    rent_2024 = [r for r in mietspiegel_data if r.get("year") == 2024 and r.get("nettokaltmiete_pro_qm")]
    by_district = defaultdict(list)
    for r in rent_2024:
        by_district[r["stadtteil"]].append(r["nettokaltmiete_pro_qm"])

    district_rent = [
        {"district": d, "avg_rent": round(sum(v) / len(v), 2)}
        for d, v in sorted(by_district.items(), key=lambda x: sum(x[1]) / len(x[1]), reverse=True)
    ]

    avg_city_rent = round(sum(r["avg_rent"] for r in district_rent) / len(district_rent), 2) if district_rent else 0

    return {
        "districts": len(districts_geojson.get("features", [])),
        "avg_rent": avg_city_rent,
        "rent_by_district": district_rent,
        "insight": generate_rent_insight(district_rent, avg_city_rent),
    }


def process_economy_data(tax_revenue: list) -> dict:
    """Process economy and tax data."""
    if not tax_revenue:
        return {"total_revenue": 0}

    revenue_trend = []
    for row in sorted(tax_revenue, key=lambda r: r.get("jahr", 0)):
        total = sum(v for k, v in row.items() if k != "jahr" and v is not None)
        revenue_trend.append({"year": row["jahr"], "total": round(total / 1_000_000, 2)})  # Millions

    return {
        "revenue_trend": revenue_trend,
        "latest_year": revenue_trend[-1]["year"] if revenue_trend else 0,
        "latest_revenue": revenue_trend[-1]["total"] if revenue_trend else 0,
        "insight": generate_tax_insight(revenue_trend),
    }


def process_quality_data(cafes_geojson: dict) -> dict:
    """Process quality of life data."""
    return {
        "cafes_count": len(cafes_geojson.get("features", [])),
        "insight": "Magdeburg bietet eine vielfältige Café- und Restaurantszene.",
    }


def generate_climate_insight(climate_trend: list) -> str:
    """Generate climate insight."""
    if len(climate_trend) < 2:
        return ""

    first_temp = climate_trend[0]["avg_temp"]
    last_temp = climate_trend[-1]["avg_temp"]
    diff = round(last_temp - first_temp, 1)

    if diff > 0:
        return f"Magdeburg hat sich seit {climate_trend[0]['year']} um {diff}°C erwärmt"
    else:
        return f"Die Durchschnittstemperatur ist seit {climate_trend[0]['year']} relativ stabil"


def generate_accident_insight(by_year: dict, by_type: dict) -> str:
    """Generate accident insight."""
    if len(by_year) < 2:
        return ""

    years = sorted(by_year.keys())
    first_year, last_year = years[0], years[-1]
    first_count, last_count = by_year[first_year], by_year[last_year]

    if last_count > first_count:
        increase = round(((last_count - first_count) / first_count) * 100)
        return f"Unfälle sind von {first_year} bis {last_year} um {increase}% gestiegen"
    else:
        decrease = round(((first_count - last_count) / first_count) * 100)
        return f"Unfälle sind von {first_year} bis {last_year} um {decrease}% gesunken"


def generate_rent_insight(district_rent: list, avg_rent: float) -> str:
    """Generate rent insight."""
    if not district_rent:
        return ""

    most_expensive = district_rent[0]
    least_expensive = district_rent[-1]

    return f"Die teuerste Gegend ist {most_expensive['district']} (€{most_expensive['avg_rent']}/m²), die günstigste ist {least_expensive['district']} (€{least_expensive['avg_rent']}/m²)"


def generate_tax_insight(revenue_trend: list) -> str:
    """Generate tax revenue insight."""
    if len(revenue_trend) < 2:
        return ""

    first_rev = revenue_trend[0]["total"]
    last_rev = revenue_trend[-1]["total"]
    growth = round(((last_rev - first_rev) / first_rev) * 100)

    return f"Steuereinnahmen sind seit {revenue_trend[0]['year']} um {growth}% gewachsen"


def generate_facts(trees_data: list, accidents_data: list, climate_monthly: list, mietspiegel_data: list, tax_revenue: list) -> list[dict]:
    """Generate 'Wussten Sie, dass...' facts."""
    facts = []

    # Tree fact
    if trees_data:
        facts.append({
            "category": "Umwelt",
            "text": f"Magdeburg hat über {len(trees_data):,} registrierte Straßenbäume".replace(",", "."),
            "source": "Baumkataster Magdeburg 2024",
        })

    # Climate fact
    if climate_monthly:
        facts.append({
            "category": "Klima",
            "text": "Otto von Guericke erfand 1654 die Vakuumpumpe in Magdeburg",
            "source": "Historische Aufzeichnungen",
        })

    # Accident fact
    if accidents_data:
        bike_accidents = sum(1 for a in accidents_data if a.get("ist_rad"))
        facts.append({
            "category": "Mobilität",
            "text": f"Von {len(accidents_data):,} Unfällen waren {bike_accidents:,} Fahrradunfälle".replace(",", "."),
            "source": "Unfallatlas Magdeburg 2016-2023",
        })

    # Rent fact
    if mietspiegel_data:
        facts.append({
            "category": "Wohnen",
            "text": "Die Mietpreise variieren stark zwischen den Stadtteilen",
            "source": "Mietspiegel Magdeburg 2024",
        })

    # Tax fact
    if tax_revenue:
        facts.append({
            "category": "Wirtschaft",
            "text": "Die Steuereinnahmen der Stadt zeigen einen positiven Wachstumstrend",
            "source": "Steuereinnahmen-Statistik",
        })

    # Cultural fact
    facts.append({
        "category": "Kultur",
        "text": "Die Grüne Zitadelle ist Hundertwassers letztes Bauwerk",
        "source": "Architekturgeschichte",
    })

    # Population fact
    facts.append({
        "category": "Bevölkerung",
        "text": "Magdeburg ist die Landeshauptstadt von Sachsen-Anhalt",
        "source": "Öffentliche Information",
    })

    return facts


def save_processed_data():
    """Process and save all data to static/data directory."""
    print("Processing all datasets...")

    # Import and initialize data loader
    from app.data_loader import load_all
    print("Loading raw data...")
    load_all()
    print("Raw data loaded!")

    data = process_all_data()

    output_dir = Path(__file__).parent / "static" / "data"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save individual files
    for key, value in data.items():
        output_file = output_dir / f"{key}.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
        print(f"✓ Saved {output_file}")

    print("✓ Data processing complete!")


if __name__ == "__main__":
    save_processed_data()
