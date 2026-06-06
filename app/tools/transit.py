from collections import Counter

from app.data_loader import transit_stops
from app.tools import register_tool


def nahverkehr(suche: str = "", typ: str = "") -> str:
    if not transit_stops:
        return "ÖPNV-Daten nicht verfügbar."

    filtered = transit_stops
    if typ:
        t_lower = typ.lower()
        if "tram" in t_lower or "straßenbahn" in t_lower or "strassenbahn" in t_lower:
            filtered = [s for s in filtered if s["typ"] == "Straßenbahn"]
        elif "bus" in t_lower:
            filtered = [s for s in filtered if "Bus" in s["typ"]]
    if suche:
        q = suche.lower()
        filtered = [s for s in filtered if q in s["name"].lower()]

    if not filtered:
        return f"Keine Haltestellen gefunden für suche='{suche}', typ='{typ}'."

    total = len(transit_stops)
    count = len(filtered)
    by_type = Counter(s["typ"] for s in filtered)

    lines = [f"ÖPNV-Haltestellen in Magdeburg:"]
    if suche or typ:
        lines[0] = f"ÖPNV-Haltestellen ({count} Treffer):"

    lines.append(f"  Gesamt: {total} Haltestellen")
    lines.append("  Nach Typ:")
    for t, c in by_type.most_common():
        lines.append(f"    - {t}: {c}")

    if suche and count <= 10:
        lines.append("  Ergebnisse:")
        for s in filtered:
            lines.append(f"    - {s['name']} ({s['typ']})")

    lines.append("Quelle: NASA GmbH (Nahverkehrsservice Sachsen-Anhalt)")
    return "\n".join(lines)


register_tool(
    name="nahverkehr",
    description="ÖPNV-Haltestellen in Magdeburg suchen (Straßenbahn, Bus, PlusBus)",
    parameters={
        "type": "object",
        "properties": {
            "suche": {
                "type": "string",
                "description": "Haltestellenname (z.B. 'Hasselbachplatz', 'Hauptbahnhof')",
            },
            "typ": {
                "type": "string",
                "description": "Typ: Straßenbahn, Bus, PlusBus",
            },
        },
        "required": [],
    },
    handler=nahverkehr,
)
