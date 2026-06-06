import json
from pathlib import Path

from app.tools import register_tool

DATA_PATH = Path(__file__).parent.parent.parent / "data" / "CafesOSM" / "CafesOSM.geojson"

_cafes: list[dict] = []


def _load_cafes():
    global _cafes
    if _cafes:
        return
    with open(DATA_PATH, encoding="utf-8") as f:
        geojson = json.load(f)
    for feature in geojson.get("features", []):
        props = feature.get("properties", {})
        coords = feature.get("geometry", {}).get("coordinates", [])
        _cafes.append({
            "name": props.get("name", "Unbekannt"),
            "street": props.get("addr:street", ""),
            "housenumber": props.get("addr:housenumber", ""),
            "website": props.get("website", ""),
            "opening_hours": props.get("opening_hours", ""),
            "lon": coords[0] if len(coords) >= 2 else None,
            "lat": coords[1] if len(coords) >= 2 else None,
        })


def cafes_suche(suche: str = "") -> str:
    _load_cafes()
    results = _cafes
    if suche:
        query = suche.lower()
        results = [
            c for c in _cafes
            if query in c["name"].lower()
            or query in c["street"].lower()
        ]

    if not results:
        return f"Keine Cafés gefunden für '{suche}'."

    total = len(_cafes)
    shown = results[:10]
    lines = [f"Cafés in Magdeburg ({total} insgesamt):"]
    if suche:
        lines[0] = f"Cafés passend zu '{suche}' ({len(results)} Treffer):"

    for c in shown:
        addr = f"{c['street']} {c['housenumber']}".strip()
        line = f"- {c['name']}"
        if addr:
            line += f", {addr}"
        if c["opening_hours"]:
            line += f" (Öffnungszeiten: {c['opening_hours']})"
        lines.append(line)

    if len(results) > 10:
        lines.append(f"... und {len(results) - 10} weitere.")
    lines.append("Quelle: OpenStreetMap")
    return "\n".join(lines)


register_tool(
    name="cafes",
    description="Cafés in Magdeburg suchen (Name oder Straße)",
    parameters={
        "type": "object",
        "properties": {
            "suche": {
                "type": "string",
                "description": "Suchbegriff (Name oder Straße). Leer für alle Cafés.",
            }
        },
        "required": [],
    },
    handler=cafes_suche,
)
