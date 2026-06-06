from collections import Counter

from app.data_loader import trees_data
from app.tools import register_tool


def baum_statistik(stadtteil: str = "", art: str = "", frage_typ: str = "anzahl") -> str:
    if not trees_data:
        return "Baumdaten nicht verfügbar."

    filtered = trees_data
    if stadtteil:
        q = stadtteil.lower()
        filtered = [t for t in filtered if q in t["stadtteil"].lower()]
    if art:
        q = art.lower()
        filtered = [t for t in filtered if q in t["gattungsgruppe"].lower() or q in t["gattung"].lower()]

    if not filtered:
        return f"Keine Bäume gefunden für Stadtteil='{stadtteil}', Art='{art}'."

    total = len(trees_data)
    count = len(filtered)

    if frage_typ == "arten":
        species = Counter(t["gattungsgruppe"] for t in filtered)
        top10 = species.most_common(10)
        lines = [f"Baumarten in {'Stadtteil ' + stadtteil if stadtteil else 'Magdeburg'} ({count} Bäume):"]
        for name, n in top10:
            lines.append(f"  - {name}: {n:,} ({n*100//count}%)")
        lines.append(f"Quelle: Baumkataster Magdeburg ({total:,} Bäume gesamt)")
        return "\n".join(lines)

    elif frage_typ == "alter":
        years = [t["pflanzjahr"] for t in filtered if t["pflanzjahr"] and t["pflanzjahr"] > 1800]
        if not years:
            return "Keine Pflanzjahrdaten verfügbar."
        decades = Counter((int(y) // 10) * 10 for y in years)
        top = decades.most_common(5)
        avg_year = sum(years) // len(years)
        lines = [f"Altersverteilung ({count} Bäume, Durchschnitt Pflanzjahr: {avg_year}):"]
        for decade, n in sorted(top):
            lines.append(f"  - {decade}er: {n:,} Bäume")
        return "\n".join(lines)

    elif frage_typ == "hoehe":
        heights = [t["baumhoehe"] for t in filtered if t["baumhoehe"] and t["baumhoehe"] > 0]
        if not heights:
            return "Keine Höhendaten verfügbar."
        avg_h = sum(heights) / len(heights)
        return (
            f"Baumhöhen ({'Stadtteil ' + stadtteil if stadtteil else 'Magdeburg'}, {len(heights)} Bäume):\n"
            f"  - Durchschnitt: {avg_h:.1f} m\n"
            f"  - Minimum: {min(heights):.1f} m\n"
            f"  - Maximum: {max(heights):.1f} m"
        )

    else:
        species = Counter(t["gattungsgruppe"] for t in filtered)
        top5 = species.most_common(5)
        districts = Counter(t["stadtteil"] for t in filtered)
        top_district = districts.most_common(3)
        lines = [f"Baumstatistik Magdeburg:"]
        lines.append(f"  - Gesamt: {total:,} Bäume")
        if stadtteil or art:
            lines.append(f"  - Gefiltert: {count:,} Bäume")
        lines.append(f"  - Top Arten: {', '.join(f'{n} ({c:,})' for n, c in top5)}")
        if not stadtteil:
            lines.append(f"  - Top Stadtteile: {', '.join(f'{n} ({c:,})' for n, c in top_district)}")
        lines.append("Quelle: Baumkataster Magdeburg")
        return "\n".join(lines)


register_tool(
    name="baum_statistik",
    description="Statistiken über Stadtbäume in Magdeburg (Anzahl, Arten, Alter, Höhe pro Stadtteil)",
    parameters={
        "type": "object",
        "properties": {
            "stadtteil": {
                "type": "string",
                "description": "Stadtteil-Filter (z.B. 'Buckau', 'Altstadt'). Leer für ganz Magdeburg.",
            },
            "art": {
                "type": "string",
                "description": "Baumart-Filter (z.B. 'Linde', 'Eiche', 'Ahorn')",
            },
            "frage_typ": {
                "type": "string",
                "enum": ["anzahl", "arten", "alter", "hoehe"],
                "description": "Art der Statistik: anzahl (Übersicht), arten (Artenverteilung), alter (Pflanzjahre), hoehe (Höhenstatistik)",
            },
        },
        "required": [],
    },
    handler=baum_statistik,
)
