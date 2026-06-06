from app.data_loader import (
    climate_energy_emissions,
    climate_led_streetlights,
    climate_monthly,
    climate_solar_energy,
)
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


def energie_klima_trends(thema: str = "uebersicht") -> str:
    thema = (thema or "uebersicht").lower()

    if thema == "energie":
        if not climate_energy_emissions:
            return "Energy and emissions data for Magdeburg are currently unavailable."

        latest = climate_energy_emissions[-1]
        first = climate_energy_emissions[0]
        total_change_pct = ((latest["total"] - first["total"]) / first["total"]) * 100 if first["total"] else 0

        lines = [
            f"Energy and emissions in Magdeburg ({latest['year']}):",
            f"  - Total final energy consumption: {latest['total']:,.0f} MWh".replace(",", "."),
            f"  - Households: {latest['haushalte']:,.0f} MWh".replace(",", "."),
            f"  - Industry: {latest['industrie']:,.0f} MWh".replace(",", "."),
            f"  - Commerce/services: {latest['ghd']:,.0f} MWh".replace(",", "."),
            f"  - Transport: {latest['verkehr']:,.0f} MWh".replace(",", "."),
            f"  - Change since {first['year']}: {total_change_pct:+.1f}%",
            "Source: Stabstelle Klima Magdeburg",
        ]
        return "\n".join(lines)

    if thema == "solar":
        if not climate_solar_energy:
            return "Solar energy data for Magdeburg are currently unavailable."

        lines = [
            "Solar energy in Magdeburg:",
            f"  - PV installations: {climate_solar_energy['total_installations']:,}".replace(",", "."),
            f"  - Installed capacity: {climate_solar_energy['installed_capacity_mw']:.2f} MW",
            f"  - Annual generation: {climate_solar_energy['annual_generation_gwh']:.1f} GWh",
            "Source: Stabstelle Klima Magdeburg",
        ]
        return "\n".join(lines)

    if thema == "led":
        if not climate_led_streetlights:
            return "LED streetlight data for Magdeburg are currently unavailable."

        lines = [
            "LED streetlights in Magdeburg:",
            f"  - Total streetlights: {climate_led_streetlights['total_streetlights']:,}".replace(",", "."),
            f"  - Converted to LED: {climate_led_streetlights['led_converted']:,}".replace(",", "."),
            f"  - Still conventional: {climate_led_streetlights['conventional']:,}".replace(",", "."),
            f"  - LED conversion rate: {climate_led_streetlights['led_percentage']:.1f}%",
            "Source: Stabstelle Klima Magdeburg",
        ]
        return "\n".join(lines)

    parts = []
    if climate_energy_emissions:
        latest = climate_energy_emissions[-1]
        parts.append(
            f"- **Energy**: Total final energy consumption in {latest['year']} was {latest['total']:,.0f} MWh.".replace(",", ".")
        )
    if climate_solar_energy:
        parts.append(
            f"- **Solar**: Magdeburg has {climate_solar_energy['total_installations']:,} PV installations with {climate_solar_energy['installed_capacity_mw']:.2f} MW installed capacity and {climate_solar_energy['annual_generation_gwh']:.1f} GWh annual generation.".replace(",", ".")
        )
    if climate_led_streetlights:
        parts.append(
            f"- **LED streetlights**: {climate_led_streetlights['led_percentage']:.1f}% of Magdeburg's {climate_led_streetlights['total_streetlights']:,} streetlights have been converted to LED.".replace(",", ".")
        )

    if not parts:
        return "Climate office data for Magdeburg are currently unavailable."

    return "Smart City climate and energy overview for Magdeburg:\n" + "\n".join(parts) + "\nSource: Stabstelle Klima Magdeburg"


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

register_tool(
    name="energie_klima_trends",
    description="Energy, solar and LED streetlight trends for Magdeburg from the Climate Office (energy consumption, PV generation, LED conversion)",
    parameters={
        "type": "object",
        "properties": {
            "thema": {
                "type": "string",
                "enum": ["uebersicht", "energie", "solar", "led"],
                "description": "Overview, energy/emissions, solar energy or LED streetlights.",
            },
        },
        "required": [],
    },
    handler=energie_klima_trends,
)
