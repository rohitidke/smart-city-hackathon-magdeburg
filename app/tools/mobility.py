from app.data_loader import kiss_public_transport, kiss_vehicle_fleet
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


def mobilitaet_trends(thema: str = "uebersicht", sprache: str = "de") -> str:
    thema = (thema or "uebersicht").lower()
    sprache = "en" if (sprache or "").lower().startswith("en") else "de"

    latest_transit = kiss_public_transport[-1] if kiss_public_transport else None
    first_transit = kiss_public_transport[0] if kiss_public_transport else None
    latest_vehicles = kiss_vehicle_fleet[-1] if kiss_vehicle_fleet else None
    first_vehicles = kiss_vehicle_fleet[0] if kiss_vehicle_fleet else None

    if thema == "oepnv":
        if not latest_transit or not first_transit:
            return (
                "Public transport trend data for Magdeburg are currently unavailable."
                if sprache == "en"
                else "ÖPNV-Trenddaten für Magdeburg sind derzeit nicht verfügbar."
            )

        lines = (
            [
                f"Public transport in Magdeburg ({latest_transit['var1']}):",
                f"  - Reported passengers: {_format_int(latest_transit.get('var2'))}",
                f"  - Change since {first_transit['var1']}: {_format_percent(latest_transit['var2'], first_transit['var2'])}",
                "  - Note: only the total passenger count is used because the subcategories in the source are not reliably labeled.",
                "Source: KISS-MD transport statistics",
            ]
            if sprache == "en"
            else [
                f"ÖPNV in Magdeburg ({latest_transit['var1']}):",
                f"  - Gemeldete Fahrgäste: {_format_int(latest_transit.get('var2'))}",
                f"  - Veränderung seit {first_transit['var1']}: {_format_percent(latest_transit['var2'], first_transit['var2'])}",
                "  - Hinweis: Es wird nur die Gesamtzahl der Fahrgäste verwendet, da die Unterkategorien der Quelle nicht zuverlässig beschriftet sind.",
                "Quelle: KISS-MD Verkehrsstatistik",
            ]
        )
        return "\n".join(lines)

    if thema == "fahrzeuge":
        if not latest_vehicles or not first_vehicles:
            return (
                "Vehicle fleet data for Magdeburg are currently unavailable."
                if sprache == "en"
                else "Daten zum Fahrzeugbestand in Magdeburg sind derzeit nicht verfügbar."
            )

        lines = (
            [
                f"Vehicle fleet in Magdeburg ({latest_vehicles['var1']}):",
                f"  - Total vehicles: {_format_int(latest_vehicles.get('var2'))}",
                f"  - Change since {first_vehicles['var1']}: {_format_percent(latest_vehicles['var2'], first_vehicles['var2'])}",
                f"  - Motorcycles: {_format_int(latest_vehicles.get('var5'))}",
                f"  - Transporters: {_format_int(latest_vehicles.get('var9'))}",
                "  - Note: several additional vehicle-type columns in the source are left unused because they are not reliably labeled.",
                "Source: KISS-MD transport statistics",
            ]
            if sprache == "en"
            else [
                f"Fahrzeugbestand in Magdeburg ({latest_vehicles['var1']}):",
                f"  - Kraftfahrzeuge gesamt: {_format_int(latest_vehicles.get('var2'))}",
                f"  - Veränderung seit {first_vehicles['var1']}: {_format_percent(latest_vehicles['var2'], first_vehicles['var2'])}",
                f"  - Motorräder: {_format_int(latest_vehicles.get('var5'))}",
                f"  - Transporter: {_format_int(latest_vehicles.get('var9'))}",
                "  - Hinweis: Mehrere weitere Fahrzeugtyp-Spalten der Quelle werden nicht genutzt, weil sie nicht zuverlässig beschriftet sind.",
                "Quelle: KISS-MD Verkehrsstatistik",
            ]
        )
        return "\n".join(lines)

    parts = []
    if latest_transit and first_transit:
        parts.append(
            (
                f"- **Public transport**: {_format_int(latest_transit.get('var2'))} reported passengers in {latest_transit['var1']} ({_format_percent(latest_transit['var2'], first_transit['var2'])} since {first_transit['var1']})."
                if sprache == "en"
                else f"- **ÖPNV**: {_format_int(latest_transit.get('var2'))} gemeldete Fahrgäste im Jahr {latest_transit['var1']} ({_format_percent(latest_transit['var2'], first_transit['var2'])} seit {first_transit['var1']})."
            )
        )
    if latest_vehicles and first_vehicles:
        parts.append(
            (
                f"- **Vehicle fleet**: {_format_int(latest_vehicles.get('var2'))} total vehicles in {latest_vehicles['var1']} ({_format_percent(latest_vehicles['var2'], first_vehicles['var2'])} since {first_vehicles['var1']})."
                if sprache == "en"
                else f"- **Fahrzeugbestand**: {_format_int(latest_vehicles.get('var2'))} Kraftfahrzeuge gesamt im Jahr {latest_vehicles['var1']} ({_format_percent(latest_vehicles['var2'], first_vehicles['var2'])} seit {first_vehicles['var1']})."
            )
        )

    if not parts:
        return (
            "Mobility trend data for Magdeburg are currently unavailable."
            if sprache == "en"
            else "Mobilitätstrends für Magdeburg sind derzeit nicht verfügbar."
        )

    heading = (
        "Mobility trends in Magdeburg:"
        if sprache == "en"
        else "Mobilitätstrends in Magdeburg:"
    )
    note = (
        "Note: only clearly interpretable aggregate fields are used from the KISS-MD transport datasets."
        if sprache == "en"
        else "Hinweis: Aus den KISS-MD-Verkehrsdatensätzen werden nur eindeutig interpretierbare Summenfelder genutzt."
    )
    source = (
        "Source: KISS-MD transport statistics"
        if sprache == "en"
        else "Quelle: KISS-MD Verkehrsstatistik"
    )
    return f"{heading}\n" + "\n".join(parts) + f"\n{note}\n{source}"


register_tool(
    name="mobilitaet_trends",
    description="Mobility trends for Magdeburg: public transport passenger development and vehicle fleet development from KISS-MD.",
    parameters={
        "type": "object",
        "properties": {
            "thema": {
                "type": "string",
                "enum": ["uebersicht", "oepnv", "fahrzeuge"],
                "description": "Overview, public transport trends, or vehicle fleet trends.",
            },
            "sprache": {
                "type": "string",
                "enum": ["de", "en"],
                "description": "Antwortsprache.",
            },
        },
        "required": [],
    },
    handler=mobilitaet_trends,
)
