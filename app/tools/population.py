from app.data_loader import kiss_population_monthly, zensus_pop, zensus_rent
from app.tools import register_tool


def bevoelkerung() -> str:
    if kiss_population_monthly:
        latest_row = next(
            (row for row in reversed(kiss_population_monthly) if row.get("var5")),
            None,
        )
        if latest_row:
            total_pop = latest_row.get("var5")
            year = str(latest_row.get("var1", ""))[:4] or "aktuell"
            month = latest_row.get("var2")

            lines = [
                "Population of Magdeburg (KISS-MD):",
                f"  - Total population: {int(total_pop):,}".replace(",", "."),
            ]
            if month:
                lines.append(f"  - Reference period: {month}/{year}")
            else:
                lines.append(f"  - Reference year: {year}")
            lines.append("Source: KISS-MD population statistics")
            return "\n".join(lines)

    if not zensus_pop:
        return "Population data for Magdeburg is currently unavailable."

    total_pop = sum(z["einwohner"] for z in zensus_pop)
    cells_with_data = len(zensus_pop)
    avg_per_cell = total_pop / cells_with_data if cells_with_data else 0

    lines = [
        "Population of Magdeburg (Census grid data):",
        f"  - Total population: approx. {total_pop:,}",
        f"  - Grid cells with residents: {cells_with_data:,}",
        f"  - Average residents per cell: {avg_per_cell:.0f}",
    ]

    if zensus_rent:
        rents = [z["miete_qm"] for z in zensus_rent if z.get("miete_qm") is not None]
        if rents:
            avg_rent = sum(rents) / len(rents)
            lines.append(f"  - Average net cold rent (census): {avg_rent:.2f} €/m²")

    lines.append("Source: Census 2011 (grid cells)")
    return "\n".join(lines)


register_tool(
    name="bevoelkerung",
    description="Bevölkerungsdaten für Magdeburg (Einwohner, Dichte)",
    parameters={"type": "object", "properties": {}, "required": []},
    handler=bevoelkerung,
)
