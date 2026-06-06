from app.data_loader import climate_monthly
from app.tools import register_tool


def klima_daten(zeitraum: str = "aktuell", jahr: int = 0) -> str:
    if not climate_monthly:
        return "Klimadaten nicht verfügbar."

    if zeitraum == "jahr" and jahr:
        rows = [r for r in climate_monthly if r.get("date", "").startswith(str(jahr))]
        if not rows:
            return f"Keine Klimadaten für das Jahr {jahr}."
        temps = [r["MO_TT"] for r in rows if r.get("MO_TT") is not None]
        precip = [r["MO_RR"] for r in rows if r.get("MO_RR") is not None]
        sun = [r["MO_SD_S"] for r in rows if r.get("MO_SD_S") is not None]
        lines = [f"Klima in Magdeburg {jahr}:"]
        if temps:
            lines.append(f"  - Jahresdurchschnitt Temperatur: {sum(temps)/len(temps):.1f}°C")
            lines.append(f"  - Kältester Monat: {min(temps):.1f}°C, Wärmster: {max(temps):.1f}°C")
        if precip:
            lines.append(f"  - Jahres-Niederschlag: {sum(precip):.0f} mm")
        if sun:
            lines.append(f"  - Sonnenstunden gesamt: {sum(sun):.0f} h")
        lines.append("Quelle: DWD — Climate Data Center")
        return "\n".join(lines)

    elif zeitraum == "historisch":
        decade_temps = {}
        for r in climate_monthly:
            if r.get("MO_TT") is None or not r.get("date"):
                continue
            try:
                year = int(r["date"][:4])
            except (ValueError, TypeError):
                continue
            decade = (year // 10) * 10
            if decade not in decade_temps:
                decade_temps[decade] = []
            decade_temps[decade].append(r["MO_TT"])

        lines = ["Historische Temperaturentwicklung Magdeburg (Dekaden-Durchschnitt):"]
        for decade in sorted(decade_temps.keys()):
            if decade < 1880:
                continue
            vals = decade_temps[decade]
            avg = sum(vals) / len(vals)
            lines.append(f"  - {decade}er: {avg:.1f}°C")
        lines.append("Quelle: DWD — Climate Data Center (Daten seit 1834)")
        return "\n".join(lines)

    else:
        recent = [r for r in climate_monthly if r.get("date", "") >= "2024"]
        if not recent:
            recent = climate_monthly[-12:]
        temps = [r["MO_TT"] for r in recent if r.get("MO_TT") is not None]
        precip = [r["MO_RR"] for r in recent if r.get("MO_RR") is not None]
        lines = ["Aktuelle Klimadaten Magdeburg (letzte 12 Monate):"]
        if temps:
            lines.append(f"  - Durchschnitt: {sum(temps)/len(temps):.1f}°C")
            lines.append(f"  - Min: {min(temps):.1f}°C, Max: {max(temps):.1f}°C")
        if precip:
            lines.append(f"  - Niederschlag gesamt: {sum(precip):.0f} mm")
        lines.append("Quelle: DWD — Climate Data Center")
        return "\n".join(lines)


register_tool(
    name="klima_daten",
    description="Historische und aktuelle Klimadaten für Magdeburg (Temperatur, Niederschlag, Sonnenstunden)",
    parameters={
        "type": "object",
        "properties": {
            "zeitraum": {
                "type": "string",
                "enum": ["aktuell", "jahr", "historisch"],
                "description": "aktuell (letzte 12 Monate), jahr (bestimmtes Jahr), historisch (Dekaden-Trend)",
            },
            "jahr": {
                "type": "integer",
                "description": "Jahr für zeitraum='jahr' (1834-2026)",
            },
        },
        "required": [],
    },
    handler=klima_daten,
)
