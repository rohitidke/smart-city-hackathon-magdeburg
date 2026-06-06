from app.data_loader import kiss_apprentices, kiss_employment, kiss_gdp
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


def _apprentice_total(row: dict) -> int | None:
    values = [row.get("var2"), row.get("var3"), row.get("var4")]
    numeric_values = [value for value in values if isinstance(value, (int, float))]
    if not numeric_values:
        return None
    # The source includes one ambiguous split column; the largest value is the
    # stable total used for reporting here.
    return int(max(numeric_values))


def wirtschaft_trends(thema: str = "uebersicht", sprache: str = "de") -> str:
    thema = (thema or "uebersicht").lower()
    sprache = "en" if (sprache or "").lower().startswith("en") else "de"

    latest_gdp = kiss_gdp[-1] if kiss_gdp else None
    first_gdp = kiss_gdp[0] if kiss_gdp else None
    latest_employment = kiss_employment[-1] if kiss_employment else None
    first_employment = kiss_employment[0] if kiss_employment else None
    latest_apprentices = kiss_apprentices[-1] if kiss_apprentices else None
    first_apprentices = kiss_apprentices[0] if kiss_apprentices else None

    if thema == "bip":
        if not latest_gdp or not first_gdp:
            return (
                "GDP data for Magdeburg are currently unavailable."
                if sprache == "en"
                else "BIP-Daten für Magdeburg sind derzeit nicht verfügbar."
            )

        latest_gdp_billion = latest_gdp["var2"] / 1000
        gva_billion = latest_gdp["var6"] / 1000 if latest_gdp.get("var6") is not None else None
        change_pct = _format_percent(latest_gdp["var2"], first_gdp["var2"])

        lines = (
            [
                f"GDP in Magdeburg ({latest_gdp['var1']}):",
                f"  - GDP: EUR {latest_gdp_billion:.2f} billion",
                f"  - Gross value added: EUR {gva_billion:.2f} billion" if gva_billion is not None else None,
                f"  - Employed persons in the economic accounts: {_format_int(latest_gdp.get('var5'))}",
                f"  - Change since {first_gdp['var1']}: {change_pct}",
                "Source: KISS-MD economic statistics",
            ]
            if sprache == "en"
            else [
                f"BIP in Magdeburg ({latest_gdp['var1']}):",
                f"  - Bruttoinlandsprodukt: {latest_gdp_billion:.2f} Mrd. EUR",
                f"  - Bruttowertschöpfung: {gva_billion:.2f} Mrd. EUR" if gva_billion is not None else None,
                f"  - Erwerbstätige laut Volkswirtschaftlicher Gesamtrechnung: {_format_int(latest_gdp.get('var5'))}",
                f"  - Veränderung seit {first_gdp['var1']}: {change_pct}",
                "Quelle: KISS-MD Wirtschaftsstatistik",
            ]
        )
        return "\n".join(line for line in lines if line)

    if thema == "beschaeftigung":
        if not latest_employment or not first_employment:
            return (
                "Employment data for Magdeburg are currently unavailable."
                if sprache == "en"
                else "Beschäftigungsdaten für Magdeburg sind derzeit nicht verfügbar."
            )

        change_pct = _format_percent(latest_employment["var2"], first_employment["var2"])
        lines = (
            [
                f"Employment in Magdeburg ({latest_employment['var1']}):",
                f"  - Social-insured employees at workplace: {_format_int(latest_employment.get('var2'))}",
                f"  - Change since {first_employment['var1']}: {change_pct}",
                f"  - Domestic employees: {_format_int(latest_employment.get('var12'))}",
                f"  - Foreign employees: {_format_int(latest_employment.get('var13'))}",
                "Source: KISS-MD labour market statistics",
            ]
            if sprache == "en"
            else [
                f"Beschäftigung in Magdeburg ({latest_employment['var1']}):",
                f"  - Sozialversicherungspflichtig Beschäftigte am Arbeitsort: {_format_int(latest_employment.get('var2'))}",
                f"  - Veränderung seit {first_employment['var1']}: {change_pct}",
                f"  - Deutsche Beschäftigte: {_format_int(latest_employment.get('var12'))}",
                f"  - Ausländische Beschäftigte: {_format_int(latest_employment.get('var13'))}",
                "Quelle: KISS-MD Arbeitsmarktstatistik",
            ]
        )
        return "\n".join(lines)

    if thema == "ausbildung":
        if not latest_apprentices or not first_apprentices:
            return (
                "Apprenticeship data for Magdeburg are currently unavailable."
                if sprache == "en"
                else "Ausbildungsdaten für Magdeburg sind derzeit nicht verfügbar."
            )

        latest_total = _apprentice_total(latest_apprentices)
        first_total = _apprentice_total(first_apprentices)
        change_pct = _format_percent(latest_total, first_total)

        lines = (
            [
                f"Apprenticeships in Magdeburg ({latest_apprentices['var1']}):",
                f"  - Reported apprentices at workplace: {_format_int(latest_total)}",
                f"  - Change since {first_apprentices['var1']}: {change_pct}",
                "  - Note: the source contains additional split columns with partially unclear labeling.",
                "Source: KISS-MD labour market statistics",
            ]
            if sprache == "en"
            else [
                f"Ausbildung in Magdeburg ({latest_apprentices['var1']}):",
                f"  - Gemeldete Auszubildende am Arbeitsort: {_format_int(latest_total)}",
                f"  - Veränderung seit {first_apprentices['var1']}: {change_pct}",
                "  - Hinweis: Die Quelle enthält zusätzliche Aufschlüsselungen mit teils unklarer Beschriftung.",
                "Quelle: KISS-MD Arbeitsmarktstatistik",
            ]
        )
        return "\n".join(lines)

    parts = []
    if latest_gdp and first_gdp:
        latest_gdp_billion = latest_gdp["var2"] / 1000
        parts.append(
            (
                f"- **GDP**: EUR {latest_gdp_billion:.2f} billion in {latest_gdp['var1']} ({_format_percent(latest_gdp['var2'], first_gdp['var2'])} since {first_gdp['var1']})."
                if sprache == "en"
                else f"- **BIP**: {latest_gdp_billion:.2f} Mrd. EUR im Jahr {latest_gdp['var1']} ({_format_percent(latest_gdp['var2'], first_gdp['var2'])} seit {first_gdp['var1']})."
            )
        )
    if latest_employment and first_employment:
        parts.append(
            (
                f"- **Employment**: {_format_int(latest_employment.get('var2'))} social-insured employees at workplace in {latest_employment['var1']} ({_format_percent(latest_employment['var2'], first_employment['var2'])} since {first_employment['var1']})."
                if sprache == "en"
                else f"- **Beschäftigung**: {_format_int(latest_employment.get('var2'))} sozialversicherungspflichtig Beschäftigte am Arbeitsort im Jahr {latest_employment['var1']} ({_format_percent(latest_employment['var2'], first_employment['var2'])} seit {first_employment['var1']})."
            )
        )
    if latest_apprentices and first_apprentices:
        latest_total = _apprentice_total(latest_apprentices)
        first_total = _apprentice_total(first_apprentices)
        parts.append(
            (
                f"- **Apprenticeships**: {_format_int(latest_total)} reported apprentices in {latest_apprentices['var1']} ({_format_percent(latest_total, first_total)} since {first_apprentices['var1']})."
                if sprache == "en"
                else f"- **Ausbildung**: {_format_int(latest_total)} gemeldete Auszubildende im Jahr {latest_apprentices['var1']} ({_format_percent(latest_total, first_total)} seit {first_apprentices['var1']})."
            )
        )

    if not parts:
        return (
            "Economic trend data for Magdeburg are currently unavailable."
            if sprache == "en"
            else "Wirtschaftsdaten für Magdeburg sind derzeit nicht verfügbar."
        )

    heading = (
        "Economic trends in Magdeburg:"
        if sprache == "en"
        else "Wirtschaftstrends in Magdeburg:"
    )
    source = (
        "Source: KISS-MD economic and labour market statistics"
        if sprache == "en"
        else "Quelle: KISS-MD Wirtschafts- und Arbeitsmarktstatistik"
    )
    return f"{heading}\n" + "\n".join(parts) + f"\n{source}"


register_tool(
    name="wirtschaft_trends",
    description="Economic trends for Magdeburg: GDP, employment and apprenticeships from KISS-MD.",
    parameters={
        "type": "object",
        "properties": {
            "thema": {
                "type": "string",
                "enum": ["uebersicht", "bip", "beschaeftigung", "ausbildung"],
                "description": "Overview, GDP, employment or apprenticeships.",
            },
            "sprache": {
                "type": "string",
                "enum": ["de", "en"],
                "description": "Antwortsprache.",
            },
        },
        "required": [],
    },
    handler=wirtschaft_trends,
)
