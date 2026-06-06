from app.data_loader import zensus_pop, zensus_rent
from app.tools import register_tool


def bevoelkerung() -> str:
    if not zensus_pop:
        return "Bevölkerungsdaten nicht verfügbar."

    total_pop = sum(z["einwohner"] for z in zensus_pop)
    cells_with_data = len(zensus_pop)
    avg_per_cell = total_pop / cells_with_data if cells_with_data else 0

    lines = [
        "Bevölkerung Magdeburg (Zensus-Daten):",
        f"  - Einwohner gesamt: ca. {total_pop:,}",
        f"  - Rasterzellen mit Bewohnern: {cells_with_data:,}",
        f"  - Durchschnitt pro Zelle: {avg_per_cell:.0f}",
    ]

    if zensus_rent:
        rents = [z["miete_qm"] for z in zensus_rent if z.get("miete_qm") is not None]
        if rents:
            avg_rent = sum(rents) / len(rents)
            lines.append(f"  - Durchschnittliche Nettokaltmiete (Zensus): {avg_rent:.2f} €/m²")

    lines.append("Quelle: Zensus 2011 (Rasterzellen)")
    return "\n".join(lines)


register_tool(
    name="bevoelkerung",
    description="Bevölkerungsdaten für Magdeburg (Einwohner, Dichte)",
    parameters={"type": "object", "properties": {}, "required": []},
    handler=bevoelkerung,
)
