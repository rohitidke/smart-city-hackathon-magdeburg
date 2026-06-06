from collections import Counter

from app.data_loader import accidents_data
from app.tools import register_tool

KATEGORIE_MAP = {1: "Getötete", 2: "Schwerverletzte", 3: "Leichtverletzte"}
WOCHENTAG_MAP = {1: "Sonntag", 2: "Montag", 3: "Dienstag", 4: "Mittwoch", 5: "Donnerstag", 6: "Freitag", 7: "Samstag"}


def unfall_analyse(jahr: int = 0, typ: str = "", schwere: str = "") -> str:
    if not accidents_data:
        return "Unfalldaten nicht verfügbar."

    filtered = accidents_data

    if jahr:
        filtered = [a for a in filtered if a["jahr"] == jahr]
    if typ:
        typ_lower = typ.lower()
        if "rad" in typ_lower or "fahrrad" in typ_lower:
            filtered = [a for a in filtered if a["ist_rad"] == 1]
        elif "pkw" in typ_lower or "auto" in typ_lower:
            filtered = [a for a in filtered if a["ist_pkw"] == 1]
        elif "fuss" in typ_lower or "fußgänger" in typ_lower:
            filtered = [a for a in filtered if a["ist_fuss"] == 1]
        elif "krad" in typ_lower or "motorrad" in typ_lower:
            filtered = [a for a in filtered if a["ist_krad"] == 1]
    if schwere:
        s_lower = schwere.lower()
        if "tod" in s_lower or "getötet" in s_lower:
            filtered = [a for a in filtered if a["kategorie"] == 1]
        elif "schwer" in s_lower:
            filtered = [a for a in filtered if a["kategorie"] == 2]
        elif "leicht" in s_lower:
            filtered = [a for a in filtered if a["kategorie"] == 3]

    if not filtered:
        return f"Keine Unfälle gefunden für die angegebenen Filter."

    total = len(accidents_data)
    count = len(filtered)

    by_year = Counter(a["jahr"] for a in filtered)
    by_category = Counter(a["kategorie"] for a in filtered)
    by_weekday = Counter(a["wochentag"] for a in filtered)

    lines = [f"Unfallanalyse Magdeburg ({count} Unfälle):"]
    if jahr:
        lines[0] = f"Unfallanalyse Magdeburg {jahr} ({count} Unfälle):"
    if typ:
        lines[0] = lines[0].replace(":", f" — Typ: {typ}:")

    lines.append(f"  Gesamt im Datensatz: {total} (2017–2024)")
    lines.append("  Nach Schwere:")
    for k in sorted(by_category.keys()):
        lines.append(f"    - {KATEGORIE_MAP.get(k, f'Kat.{k}')}: {by_category[k]}")

    if not jahr:
        lines.append("  Nach Jahr:")
        for y in sorted(by_year.keys()):
            lines.append(f"    - {y}: {by_year[y]}")

    peak_day = by_weekday.most_common(1)[0] if by_weekday else None
    if peak_day:
        lines.append(f"  Häufigster Wochentag: {WOCHENTAG_MAP.get(peak_day[0], '?')} ({peak_day[1]} Unfälle)")

    rad = sum(1 for a in filtered if a["ist_rad"] == 1)
    pkw = sum(1 for a in filtered if a["ist_pkw"] == 1)
    fuss = sum(1 for a in filtered if a["ist_fuss"] == 1)
    lines.append(f"  Beteiligte: Fahrrad {rad}, PKW {pkw}, Fußgänger {fuss}")
    lines.append("Quelle: Unfallatlas (Statistisches Bundesamt)")
    return "\n".join(lines)


register_tool(
    name="unfall_analyse",
    description="Verkehrsunfälle in Magdeburg analysieren (nach Jahr, Fahrzeugtyp, Schwere)",
    parameters={
        "type": "object",
        "properties": {
            "jahr": {
                "type": "integer",
                "description": "Filtere nach Jahr (2017-2024). 0 oder weglassen für alle.",
            },
            "typ": {
                "type": "string",
                "description": "Fahrzeugtyp: Fahrrad, PKW, Fußgänger, Motorrad",
            },
            "schwere": {
                "type": "string",
                "description": "Schwere: Getötete, Schwerverletzte, Leichtverletzte",
            },
        },
        "required": [],
    },
    handler=unfall_analyse,
)
