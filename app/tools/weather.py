import httpx

from app.tools import register_tool

BRIGHTSKY_URL = "https://api.brightsky.dev/current_weather"
MD_LAT = 52.1205
MD_LON = 11.6276


def wetter_aktuell() -> str:
    try:
        r = httpx.get(
            BRIGHTSKY_URL,
            params={"lat": MD_LAT, "lon": MD_LON},
            timeout=10,
        )
        r.raise_for_status()
        w = r.json()["weather"]
        return (
            f"Aktuelles Wetter in Magdeburg:\n"
            f"- Temperatur: {w.get('temperature', '?')}°C\n"
            f"- Windgeschwindigkeit: {w.get('wind_speed', '?')} km/h\n"
            f"- Niederschlag: {w.get('precipitation_60', '?')} mm/h\n"
            f"- Bewölkung: {w.get('cloud_cover', '?')}%\n"
            f"- Zustand: {w.get('condition', '?')}\n"
            f"Quelle: Bright Sky / Deutscher Wetterdienst"
        )
    except Exception as e:
        return f"Wetterdaten konnten nicht abgerufen werden: {e}"


register_tool(
    name="wetter_aktuell",
    description="Aktuelles Wetter in Magdeburg abrufen (Temperatur, Wind, Niederschlag, Bewölkung)",
    parameters={"type": "object", "properties": {}, "required": []},
    handler=wetter_aktuell,
)
