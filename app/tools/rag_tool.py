from app.rag_query import rag_is_configured, search
from app.tools import register_tool


def rag_suche(frage: str, kategorie: str = "") -> str:
    if not rag_is_configured():
        return "RAG-System nicht verfügbar (Qdrant/Ollama nicht konfiguriert)."

    try:
        cat = kategorie if kategorie else None
        hits = search(frage, k=5, category=cat)
    except Exception as e:
        return f"Fehler bei der Suche: {e}"

    if not hits:
        return f"Keine relevanten Dokumente gefunden für: '{frage}'"

    lines = [f"Relevante Quellen zu '{frage}':"]
    for hit in hits:
        p = hit.payload
        score = hit.score
        title = p.get("title", "Unbekannt")
        url = p.get("source_url", "")
        text = p.get("text", "")[:300].strip()
        lines.append(f"\n[{score:.2f}] {title}")
        if url:
            lines.append(f"  URL: {url}")
        lines.append(f"  {text}...")
    return "\n".join(lines)


if rag_is_configured():
    register_tool(
        name="rag_suche",
        description="Semantische Suche in der Magdeburg-Wissensdatenbank (71 Quellen: Strategie, Tourismus, Kultur, Geschichte, Wikipedia)",
        parameters={
            "type": "object",
            "properties": {
                "frage": {
                    "type": "string",
                    "description": "Suchanfrage / Frage (deutsch bevorzugt)",
                },
                "kategorie": {
                    "type": "string",
                    "enum": ["", "strategie", "tourismus", "kultur", "wikipedia", "historisch", "mmkt", "dates", "otto", "restaurants"],
                    "description": "Optionaler Kategorie-Filter",
                },
            },
            "required": ["frage"],
        },
        handler=rag_suche,
    )
