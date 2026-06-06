from app.data_loader import tax_revenue, tax_columns
from app.tools import register_tool


def steuer_einnahmen(jahr: int = 0) -> str:
    if not tax_revenue:
        return "Steuerdaten nicht verfügbar."

    if jahr:
        row = next((r for r in tax_revenue if r.get("jahr") == jahr), None)
        if not row:
            available = sorted(r["jahr"] for r in tax_revenue)
            return f"Keine Daten für {jahr}. Verfügbar: {available[0]}-{available[-1]}"

        lines = [f"Steuereinnahmen Magdeburg {jahr}:"]
        total = 0
        for col in tax_columns:
            key = col["key"]
            if key == "jahr":
                continue
            val = row.get(key)
            if val is not None:
                total += val
                lines.append(f"  - {col['label']}: {val:,.0f} €")
        lines.append(f"  GESAMT: {total:,.0f} €")
        lines.append("Quelle: Stadt Magdeburg — Steuerstatistik")
        return "\n".join(lines)

    lines = ["Steuereinnahmen Magdeburg (Übersicht 2010-2025):"]
    for row in sorted(tax_revenue, key=lambda r: r["jahr"]):
        total = sum(v for k, v in row.items() if k != "jahr" and v is not None)
        lines.append(f"  - {row['jahr']}: {total:,.0f} €")
    lines.append("Quelle: Stadt Magdeburg — Steuerstatistik")
    return "\n".join(lines)


register_tool(
    name="steuer_einnahmen",
    description="Steuereinnahmen der Stadt Magdeburg (2010-2025) nach Steuerart",
    parameters={
        "type": "object",
        "properties": {
            "jahr": {
                "type": "integer",
                "description": "Jahr (2010-2025). Leer für Übersicht aller Jahre.",
            },
        },
        "required": [],
    },
    handler=steuer_einnahmen,
)
