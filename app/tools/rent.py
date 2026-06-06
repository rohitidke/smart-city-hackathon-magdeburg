from collections import defaultdict

from app.data_loader import mietspiegel_baualter, mietspiegel_wohnflaeche
from app.tools import register_tool


def miete_preise(stadtteil: str = "", jahr: int = 2024) -> str:
    if not mietspiegel_baualter and not mietspiegel_wohnflaeche:
        return "Mietspiegeldaten nicht verfügbar."

    data = mietspiegel_wohnflaeche if mietspiegel_wohnflaeche else mietspiegel_baualter
    filtered = [r for r in data if r.get("year") == jahr and r.get("nettokaltmiete_pro_qm") is not None]

    if stadtteil:
        q = stadtteil.lower()
        filtered = [r for r in filtered if q in r.get("stadtteil", "").lower()]

    if not filtered:
        available_years = sorted(set(r["year"] for r in data if r.get("nettokaltmiete_pro_qm") is not None))
        return f"Keine Mietdaten für {stadtteil or 'Magdeburg'} im Jahr {jahr}. Verfügbare Jahre: {available_years}"

    by_district = defaultdict(list)
    for r in filtered:
        by_district[r["stadtteil"]].append(r["nettokaltmiete_pro_qm"])

    lines = [f"Nettokaltmiete pro m² in {'Stadtteil ' + stadtteil if stadtteil else 'Magdeburg'} ({jahr}):"]
    sorted_districts = sorted(by_district.items(), key=lambda x: sum(x[1]) / len(x[1]), reverse=True)

    for district, values in sorted_districts[:15]:
        avg = sum(values) / len(values)
        lines.append(f"  - {district}: {avg:.2f} €/m²")

    all_values = [v for vals in by_district.values() for v in vals]
    overall_avg = sum(all_values) / len(all_values)
    lines.append(f"\n  Durchschnitt gesamt: {overall_avg:.2f} €/m²")
    lines.append(f"  Stadtteile mit Daten: {len(by_district)}")
    lines.append("Quelle: Mietspiegel Magdeburg 2024")
    return "\n".join(lines)


register_tool(
    name="miete_preise",
    description="Mietpreise (Nettokaltmiete pro m²) in Magdeburg nach Stadtteil",
    parameters={
        "type": "object",
        "properties": {
            "stadtteil": {
                "type": "string",
                "description": "Stadtteil (z.B. 'Buckau', 'Altstadt', 'Stadtfeld'). Leer für alle.",
            },
            "jahr": {
                "type": "integer",
                "description": "Jahr (2012-2024, Standard: 2024)",
            },
        },
        "required": [],
    },
    handler=miete_preise,
)
