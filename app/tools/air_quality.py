import httpx

from app.tools import register_tool

SENSOR_URL = "https://data.sensor.community/airrohr/v1/filter/area=52.1205,11.6276,10"


def luftqualitaet() -> str:
    try:
        r = httpx.get(SENSOR_URL, timeout=15)
        r.raise_for_status()
        data = r.json()

        pm10_values = []
        pm25_values = []

        for sensor in data:
            for sv in sensor.get("sensordatavalues", []):
                try:
                    val = float(sv["value"])
                    if sv["value_type"] == "P1":
                        pm10_values.append(val)
                    elif sv["value_type"] == "P2":
                        pm25_values.append(val)
                except (ValueError, KeyError):
                    continue

        lines = ["Luftqualität in Magdeburg (Bürgermessnetz):"]
        if pm10_values:
            avg_pm10 = sum(pm10_values) / len(pm10_values)
            who_pm10 = "⚠️ über WHO-Richtwert (45 µg/m³)" if avg_pm10 > 45 else "✓ unter WHO-Richtwert"
            lines.append(f"- PM10: {avg_pm10:.1f} µg/m³ ({len(pm10_values)} Sensoren) — {who_pm10}")
        if pm25_values:
            avg_pm25 = sum(pm25_values) / len(pm25_values)
            who_pm25 = "⚠️ über WHO-Richtwert (15 µg/m³)" if avg_pm25 > 15 else "✓ unter WHO-Richtwert"
            lines.append(f"- PM2.5: {avg_pm25:.1f} µg/m³ ({len(pm25_values)} Sensoren) — {who_pm25}")

        if not pm10_values and not pm25_values:
            lines.append("Keine aktuellen Messdaten verfügbar.")

        lines.append("Quelle: Sensor.Community (Bürgermessnetz)")
        return "\n".join(lines)
    except Exception as e:
        return f"Luftqualitätsdaten konnten nicht abgerufen werden: {e}"


register_tool(
    name="luftqualitaet",
    description="Aktuelle Luftqualität in Magdeburg (PM10, PM2.5 aus dem Bürgermessnetz)",
    parameters={"type": "object", "properties": {}, "required": []},
    handler=luftqualitaet,
)
