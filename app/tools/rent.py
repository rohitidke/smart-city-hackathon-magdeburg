from collections import defaultdict

from app.data_loader import mietspiegel_baualter, mietspiegel_wohnflaeche
from app.tools import register_tool


def _language_is_english(sprache: str) -> bool:
    return (sprache or "").lower().startswith("en")


def miete_preise(
    stadtteil: str = "",
    jahr: int = 2024,
    frage_typ: str = "uebersicht",
    sprache: str = "de",
) -> str:
    if not mietspiegel_baualter and not mietspiegel_wohnflaeche:
        return "Rent data for Magdeburg are currently unavailable." if _language_is_english(sprache) else "Mietspiegeldaten nicht verfügbar."

    data = mietspiegel_wohnflaeche if mietspiegel_wohnflaeche else mietspiegel_baualter
    filtered = [r for r in data if r.get("year") == jahr and r.get("nettokaltmiete_pro_qm") is not None]

    if stadtteil:
        q = stadtteil.lower()
        filtered = [r for r in filtered if q in r.get("stadtteil", "").lower()]

    if not filtered:
        available_years = sorted(set(r["year"] for r in data if r.get("nettokaltmiete_pro_qm") is not None))
        if _language_is_english(sprache):
            return f"No rent data for {stadtteil or 'Magdeburg'} in {jahr}. Available years: {available_years}"
        return f"Keine Mietdaten für {stadtteil or 'Magdeburg'} im Jahr {jahr}. Verfügbare Jahre: {available_years}"

    by_district = defaultdict(list)
    for r in filtered:
        by_district[r["stadtteil"]].append(r["nettokaltmiete_pro_qm"])

    district_averages = [
        (district, sum(values) / len(values))
        for district, values in by_district.items()
    ]
    sorted_districts = sorted(district_averages, key=lambda item: item[1], reverse=True)
    cheapest_district, cheapest_avg = min(district_averages, key=lambda item: item[1])
    highest_district, highest_avg = max(district_averages, key=lambda item: item[1])

    if frage_typ == "guenstigste":
        if _language_is_english(sprache):
            return (
                f"The cheapest district to live in Magdeburg based on net cold rent in {jahr} is "
                f"**{cheapest_district}** at an average of **{cheapest_avg:.2f} EUR/m²**.\n"
                f"Highest district average for comparison: **{highest_district}** with **{highest_avg:.2f} EUR/m²**.\n"
                "Source: Mietspiegel Magdeburg 2024"
            )
        return (
            f"Der günstigste Stadtteil zum Wohnen in Magdeburg auf Basis der Nettokaltmiete im Jahr {jahr} ist "
            f"**{cheapest_district}** mit durchschnittlich **{cheapest_avg:.2f} EUR/m²**.\n"
            f"Zum Vergleich liegt der höchste Durchschnitt in **{highest_district}** bei **{highest_avg:.2f} EUR/m²**.\n"
            "Quelle: Mietspiegel Magdeburg 2024"
        )

    if _language_is_english(sprache):
        lines = [f"Net cold rent per m² in {'district ' + stadtteil if stadtteil else 'Magdeburg'} ({jahr}):"]
    else:
        lines = [f"Nettokaltmiete pro m² in {'Stadtteil ' + stadtteil if stadtteil else 'Magdeburg'} ({jahr}):"]

    for district, avg in sorted_districts[:15]:
        lines.append(f"  - {district}: {avg:.2f} €/m²")

    overall_avg = sum(avg for _, avg in district_averages) / len(district_averages)
    if _language_is_english(sprache):
        lines.append(f"\n  Overall district average: {overall_avg:.2f} €/m²")
        lines.append(f"  Districts with data: {len(by_district)}")
        lines.append(f"  Cheapest district: {cheapest_district} ({cheapest_avg:.2f} €/m²)")
        lines.append("Source: Mietspiegel Magdeburg 2024")
    else:
        lines.append(f"\n  Durchschnitt gesamt: {overall_avg:.2f} €/m²")
        lines.append(f"  Stadtteile mit Daten: {len(by_district)}")
        lines.append(f"  Günstigster Stadtteil: {cheapest_district} ({cheapest_avg:.2f} €/m²)")
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
            "frage_typ": {
                "type": "string",
                "description": "Antworttyp: 'uebersicht' oder 'guenstigste'.",
            },
            "sprache": {
                "type": "string",
                "description": "Antwortsprache: 'de' oder 'en'.",
            },
        },
        "required": [],
    },
    handler=miete_preise,
)
