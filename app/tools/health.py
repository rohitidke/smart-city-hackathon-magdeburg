from collections import defaultdict

from app.data_loader import kiss_doctors_pharmacies, kiss_rescue_services
from app.tools import register_tool


def _format_int(value: int | float | None) -> str:
    if value is None:
        return "n/a"
    return f"{int(round(value)):,}".replace(",", ".")


def _format_percent(current: float | int | None, previous: float | int | None) -> str:
    if current in (None, 0) or previous in (None, 0):
        return "n/a"
    change = ((float(current) - float(previous)) / float(previous)) * 100
    return f"{change:+.1f}%"


def _doctors_by_year() -> list[dict]:
    by_year = defaultdict(lambda: {"doctors": 0, "pharmacies": 0})
    for row in kiss_doctors_pharmacies:
        year = row.get("var1")
        if not year:
            continue
        if row.get("var3") is not None:
            by_year[year]["doctors"] += row["var3"]
        if row.get("var5") is not None:
            by_year[year]["pharmacies"] += row["var5"]

    return [
        {"year": year, "doctors": data["doctors"], "pharmacies": data["pharmacies"]}
        for year, data in sorted(by_year.items())
    ]


def _rescue_by_year() -> list[dict]:
    by_year = defaultdict(lambda: {"deployments": 0, "months": 0})
    for row in kiss_rescue_services:
        year = row.get("var1")
        if not year or row.get("var3") is None:
            continue
        by_year[year]["deployments"] += row["var3"]
        by_year[year]["months"] += 1

    return [
        {"year": year, "deployments": data["deployments"], "months": data["months"]}
        for year, data in sorted(by_year.items())
    ]


def _latest_complete_rescue_year(rescue_years: list[dict]) -> dict | None:
    complete_years = [row for row in rescue_years if row["months"] >= 12]
    if complete_years:
        return complete_years[-1]
    return rescue_years[-1] if rescue_years else None


def gesundheitsversorgung(thema: str = "uebersicht", sprache: str = "de") -> str:
    thema = (thema or "uebersicht").lower()
    sprache = "en" if (sprache or "").lower().startswith("en") else "de"

    doctor_years = _doctors_by_year()
    rescue_years = _rescue_by_year()

    latest_doctors = doctor_years[-1] if doctor_years else None
    first_doctors = doctor_years[0] if doctor_years else None
    latest_rescue = _latest_complete_rescue_year(rescue_years)
    first_rescue = rescue_years[0] if rescue_years else None

    if thema == "aerzte":
        if not latest_doctors or not first_doctors:
            return (
                "Healthcare provider data for Magdeburg are currently unavailable."
                if sprache == "en"
                else "Daten zur Gesundheitsversorgung in Magdeburg sind derzeit nicht verfügbar."
            )

        lines = (
            [
                f"Healthcare providers in Magdeburg ({latest_doctors['year']}):",
                f"  - Doctors and practices: {_format_int(latest_doctors['doctors'])}",
                f"  - Likely pharmacies: {_format_int(latest_doctors['pharmacies'])}",
                f"  - Change in doctors/practices since {first_doctors['year']}: {_format_percent(latest_doctors['doctors'], first_doctors['doctors'])}",
                "  - Note: the KISS-MD subcategories in this dataset are only partially labeled, so pharmacy counts are treated as best-effort.",
                "Source: KISS-MD health and social statistics",
            ]
            if sprache == "en"
            else [
                f"Gesundheitsversorgung in Magdeburg ({latest_doctors['year']}):",
                f"  - Ärzte & Praxen: {_format_int(latest_doctors['doctors'])}",
                f"  - Wahrscheinlich Apotheken: {_format_int(latest_doctors['pharmacies'])}",
                f"  - Veränderung bei Ärzte & Praxen seit {first_doctors['year']}: {_format_percent(latest_doctors['doctors'], first_doctors['doctors'])}",
                "  - Hinweis: Die KISS-MD-Unterkategorien in diesem Datensatz sind nur teilweise beschriftet; die Apothekenzahl ist daher eine bestmögliche Zuordnung.",
                "Quelle: KISS-MD Gesundheit und Soziales",
            ]
        )
        return "\n".join(lines)

    if thema == "apotheken":
        if not latest_doctors:
            return (
                "Pharmacy data for Magdeburg are currently unavailable."
                if sprache == "en"
                else "Apothekendaten für Magdeburg sind derzeit nicht verfügbar."
            )

        lines = (
            [
                f"Likely pharmacies in Magdeburg ({latest_doctors['year']}):",
                f"  - Reported count: {_format_int(latest_doctors['pharmacies'])}",
                "  - Note: the category mapping in the KISS-MD source is partially ambiguous, so this number should be read as a best-effort pharmacy estimate.",
                "Source: KISS-MD health and social statistics",
            ]
            if sprache == "en"
            else [
                f"Wahrscheinliche Apotheken in Magdeburg ({latest_doctors['year']}):",
                f"  - Gemeldete Anzahl: {_format_int(latest_doctors['pharmacies'])}",
                "  - Hinweis: Die Kategorien im KISS-MD-Datensatz sind teilweise uneindeutig, daher ist dies als bestmögliche Apotheken-Schätzung zu verstehen.",
                "Quelle: KISS-MD Gesundheit und Soziales",
            ]
        )
        return "\n".join(lines)

    if thema == "rettungsdienst":
        if not latest_rescue or not first_rescue:
            return (
                "Rescue service data for Magdeburg are currently unavailable."
                if sprache == "en"
                else "Rettungsdienstdaten für Magdeburg sind derzeit nicht verfügbar."
            )

        lines = (
            [
                f"Rescue services in Magdeburg ({latest_rescue['year']}):",
                f"  - Total deployments: {_format_int(latest_rescue['deployments'])}",
                f"  - Change since {first_rescue['year']}: {_format_percent(latest_rescue['deployments'], first_rescue['deployments'])}",
                f"  - Months included: {latest_rescue['months']}",
                "Source: KISS-MD health and social statistics",
            ]
            if sprache == "en"
            else [
                f"Rettungsdienst in Magdeburg ({latest_rescue['year']}):",
                f"  - Einsätze gesamt: {_format_int(latest_rescue['deployments'])}",
                f"  - Veränderung seit {first_rescue['year']}: {_format_percent(latest_rescue['deployments'], first_rescue['deployments'])}",
                f"  - Enthaltene Monate: {latest_rescue['months']}",
                "Quelle: KISS-MD Gesundheit und Soziales",
            ]
        )
        return "\n".join(lines)

    parts = []
    if latest_doctors and first_doctors:
        parts.append(
            (
                f"- **Healthcare providers**: {_format_int(latest_doctors['doctors'])} doctors and practices in {latest_doctors['year']} ({_format_percent(latest_doctors['doctors'], first_doctors['doctors'])} since {first_doctors['year']})."
                if sprache == "en"
                else f"- **Ärzte & Praxen**: {_format_int(latest_doctors['doctors'])} im Jahr {latest_doctors['year']} ({_format_percent(latest_doctors['doctors'], first_doctors['doctors'])} seit {first_doctors['year']})."
            )
        )
        if latest_doctors["pharmacies"] is not None:
            parts.append(
                (
                    f"- **Pharmacies**: likely {_format_int(latest_doctors['pharmacies'])} in {latest_doctors['year']}."
                    if sprache == "en"
                    else f"- **Apotheken**: wahrscheinlich {_format_int(latest_doctors['pharmacies'])} im Jahr {latest_doctors['year']}."
                )
            )
    if latest_rescue and first_rescue:
        parts.append(
            (
                f"- **Rescue services**: {_format_int(latest_rescue['deployments'])} deployments in the latest complete year {latest_rescue['year']} ({_format_percent(latest_rescue['deployments'], first_rescue['deployments'])} since {first_rescue['year']})."
                if sprache == "en"
                else f"- **Rettungsdienst**: {_format_int(latest_rescue['deployments'])} Einsätze im letzten vollständigen Jahr {latest_rescue['year']} ({_format_percent(latest_rescue['deployments'], first_rescue['deployments'])} seit {first_rescue['year']})."
            )
        )

    if not parts:
        return (
            "Healthcare data for Magdeburg are currently unavailable."
            if sprache == "en"
            else "Gesundheitsdaten für Magdeburg sind derzeit nicht verfügbar."
        )

    heading = (
        "Healthcare in Magdeburg:"
        if sprache == "en"
        else "Gesundheitsversorgung in Magdeburg:"
    )
    note = (
        "Note: pharmacy counts are based on a best-effort interpretation of partially ambiguous KISS-MD category columns."
        if sprache == "en"
        else "Hinweis: Die Apothekenzahl basiert auf einer bestmöglichen Interpretation teilweise uneindeutiger KISS-MD-Kategoriespalten."
    )
    source = (
        "Source: KISS-MD health and social statistics"
        if sprache == "en"
        else "Quelle: KISS-MD Gesundheit und Soziales"
    )
    return f"{heading}\n" + "\n".join(parts) + f"\n{note}\n{source}"


register_tool(
    name="gesundheitsversorgung",
    description="Healthcare data for Magdeburg: doctors, practices, likely pharmacies, and rescue service deployments from KISS-MD.",
    parameters={
        "type": "object",
        "properties": {
            "thema": {
                "type": "string",
                "enum": ["uebersicht", "aerzte", "apotheken", "rettungsdienst"],
                "description": "Overview, doctors/practices, pharmacies, or rescue services.",
            },
            "sprache": {
                "type": "string",
                "enum": ["de", "en"],
                "description": "Antwortsprache.",
            },
        },
        "required": [],
    },
    handler=gesundheitsversorgung,
)
