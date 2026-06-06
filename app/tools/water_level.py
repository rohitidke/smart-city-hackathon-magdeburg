import httpx

from app.tools import register_tool

BASE_URL = "https://www.pegelonline.wsv.de/webservices/rest-api/v2"
STATION = "MAGDEBURG-STROMBR%C3%9CCKE"


def elbe_pegel(zeitraum: str = "aktuell") -> str:
    try:
        if zeitraum == "aktuell":
            r = httpx.get(
                f"{BASE_URL}/stations/{STATION}/W/currentmeasurement.json",
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()
            return (
                f"Aktueller Elbe-Wasserstand (Magdeburg-Strombrücke):\n"
                f"- Pegel: {data['value']} cm\n"
                f"- Zeitpunkt: {data['timestamp']}\n"
                f"Quelle: PEGELONLINE / WSV"
            )
        else:
            duration = "P1D" if zeitraum == "24h" else "P7D"
            r = httpx.get(
                f"{BASE_URL}/stations/{STATION}/W/measurements.json",
                params={"start": duration},
                timeout=10,
            )
            r.raise_for_status()
            data = r.json()
            if not data:
                return "Keine Messdaten verfügbar."
            values = [d["value"] for d in data if d.get("value") is not None]
            if not values:
                return "Keine gültigen Messwerte im Zeitraum."
            return (
                f"Elbe-Wasserstand (Magdeburg-Strombrücke) - letzte {'24 Stunden' if zeitraum == '24h' else '7 Tage'}:\n"
                f"- Minimum: {min(values)} cm\n"
                f"- Maximum: {max(values)} cm\n"
                f"- Durchschnitt: {sum(values) // len(values)} cm\n"
                f"- Aktuelle Messwerte: {len(values)}\n"
                f"Quelle: PEGELONLINE / WSV"
            )
    except Exception as e:
        return f"Pegeldaten konnten nicht abgerufen werden: {e}"


register_tool(
    name="elbe_pegel",
    description="Wasserstand der Elbe an der Station Magdeburg-Strombrücke abfragen",
    parameters={
        "type": "object",
        "properties": {
            "zeitraum": {
                "type": "string",
                "enum": ["aktuell", "24h", "7tage"],
                "description": "Zeitraum: aktuell (letzter Messwert), 24h oder 7tage",
            }
        },
        "required": [],
    },
    handler=elbe_pegel,
)
