import re

from app.llm_provider import get_provider
from app.rag_query import answer as rag_answer
from app.rag_query import rag_is_configured
from app.tools import execute_tool, get_tool_schemas

SYSTEM_PROMPT = """Du bist der Magdeburg Stadtassistent — ein KI-Assistent, der ausschließlich Fragen über Magdeburg beantwortet.

Regeln:
1. Beantworte NUR Fragen, die sich auf Magdeburg beziehen (Stadt, Geschichte, Daten, Wetter, Verkehr, Kultur, etc.).
2. Wenn der Nutzer keine Stadt nennt, aber nach lokalen Daten, Orten, Wetter, Verkehr, Cafés, Bäumen, Mieten oder ähnlichen Stadtthemen fragt, nimm IMMER an, dass Magdeburg gemeint ist.
3. Wenn der Nutzer ausdrücklich eine andere Stadt, Region oder ein anderes Land nennt, beantworte die Frage NICHT mit Magdeburg-Daten, sondern lehne höflich ab und erkläre, dass du nur Magdeburg-Fragen beantwortest.
4. Wenn eine Frage offensichtlich nichts mit Magdeburg oder städtischen Themen zu tun hat, lehne höflich ab und erkläre, dass du nur Magdeburg-Fragen beantwortest.
5. Nutze die verfügbaren Werkzeuge, um aktuelle und präzise Daten zu liefern.
6. Antworte immer in derselben Sprache wie der Nutzer. Wenn die Frage auf Englisch ist, antworte auf Englisch. Wenn die Frage auf Deutsch ist, antworte auf Deutsch.
7. Nenne Quellen, wenn verfügbar.
8. Sei präzise und hilfreich.
9. Wenn du mehrere Orte, Cafés, Ereignisse oder Punkte aufzählst, formatiere sie als echte Liste mit Zeilenumbrüchen.
10. Schreibe Listen nicht als Fließtext in einem einzigen Absatz."""

MAX_ITERATIONS = 5

LOCAL_TOPIC_KEYWORDS = {
    "air quality", "luftqualität", "weather", "wetter", "temperature", "temperatur",
    "rain", "regen", "wind", "climate", "klima", "tree", "trees", "baum", "bäume",
    "cafe", "cafes", "café", "cafés", "rent", "miete", "mietpreis", "wohnung",
    "transit", "bus", "tram", "train", "traffic", "verkehr", "haltestelle",
    "water level", "wasserstand", "elbe", "population", "bevölkerung", "school",
    "schools", "schule", "schulen", "doctor", "doctors", "arzt", "ärzte",
    "healthcare", "gesundheit", "pharmacy", "apotheke", "tourism", "tourismus",
    "hotel", "overnight stays", "übernachtungen", "tax", "steuern", "economy",
    "wirtschaft", "employment", "arbeitsmarkt", "accident", "accidents", "unfall",
    "event", "events", "veranstaltung", "veranstaltungen", "concert", "konzert",
    "festival", "show", "ausstellung", "flohmarkt",
}

RAG_QUERY_KEYWORDS = {
    "dokument", "dokumente", "quelle", "quellen", "source", "sources",
    "strategie", "strategien", "konzept", "konzepte", "isek", "smart city",
    "gefördert", "förderung", "funded", "funding", "projekt", "projekte",
    "what do the documents say", "what do the sources say", "welche aussagen",
    "fasse zusammen", "summarize", "zusammenfassung", "knowledge base",
}

DIRECT_TOOL_KEYWORDS = {
    "wetter_aktuell": {
        "weather", "wetter", "temperature", "temperatur", "rain", "regen",
        "wind", "forecast", "vorhersage",
    },
    "luftqualitaet": {
        "air quality", "luftqualität", "pm10", "pm2.5", "feinstaub",
    },
    "elbe_pegel": {
        "water level", "wasserstand", "elbe", "river level", "pegel",
    },
    "bevoelkerung": {
        "population", "people live", "einwohner", "bevölkerung", "how many people",
    },
    "steuer_einnahmen": {
        "tax revenue", "tax revenues", "steuereinnahmen", "tax income", "steuer",
    },
    "energie_klima_trends": {
        "solar", "pv", "photovoltaic", "led", "streetlight", "streetlights",
        "solar energy", "energie", "energy consumption", "emissions", "co2",
        "klima", "climate office", "street lighting",
    },
    "wirtschaft_trends": {
        "economy", "economic", "wirtschaft", "gdp", "bip", "gross value added",
        "employment", "employed", "jobs", "arbeitsmarkt", "beschäftigung",
        "apprentice", "apprentices", "auszubildende", "ausbildung", "trainee",
    },
    "gesundheitsversorgung": {
        "health", "healthcare", "gesundheit", "medical", "medizin", "doctor",
        "doctors", "arzt", "ärzte", "practice", "praxen", "pharmacy",
        "pharmacies", "apotheke", "apotheken", "rescue", "ambulance",
        "rettungsdienst", "emergency service", "notfall",
    },
    "mobilitaet_trends": {
        "mobility trends", "mobilitätstrends", "ridership", "passenger numbers",
        "public transport usage", "oepnv entwicklung", "öpnv entwicklung",
        "fahrgast", "fahrgäste", "passengers transported", "vehicle fleet",
        "kraftfahrzeugbestand", "vehicle ownership", "kfz-bestand", "car fleet",
    },
    "veranstaltungen": {
        "event", "events", "veranstaltung", "veranstaltungen", "concert",
        "konzert", "festival", "show", "market", "flohmarkt", "exhibition",
        "ausstellung", "what's on", "what is on",
    },
}

EXPLICIT_LOCATION_PATTERN = re.compile(
    r"\b(?:in|at|near|around|for|from|bei|in der|in dem|im|am|um|für)\s+([A-ZÄÖÜ][\wÄÖÜäöüß-]+)",
)
ADDRESS_PATTERN = re.compile(
    r"\b[\wÄÖÜäöüß.-]+\s+\d+[a-zA-Z]?(?:,\s*\d{5})?",
    re.IGNORECASE,
)


def should_assume_magdeburg(user_message: str) -> bool:
    lower_message = user_message.lower()
    if "magdeburg" in lower_message:
        return False

    if EXPLICIT_LOCATION_PATTERN.search(user_message):
        return False

    return any(keyword in lower_message for keyword in LOCAL_TOPIC_KEYWORDS)


def infer_language(user_message: str) -> str:
    lower_message = user_message.lower()
    tokens = set(re.findall(r"[a-zA-Zäöüß]+", lower_message))
    german_markers = {
        "und", "der", "die", "das", "ist", "sind", "welche", "was", "wie",
        "gibt", "öpnv", "für", "mit", "heute", "aktuelle", "aktuellen",
        "wieviele", "stadtteil", "wasserstand", "luftqualität",
    }
    english_markers = {
        "the", "and", "what", "which", "how", "where", "today", "current",
        "show", "give", "latest", "near", "employment", "weather", "rent",
        "population", "energy", "air", "quality",
    }

    german_score = sum(token in german_markers for token in tokens)
    english_score = sum(token in english_markers for token in tokens)

    if any(char in lower_message for char in "äöüß"):
        german_score += 1

    if english_score > german_score:
        return "en"
    if german_score > english_score:
        return "de"
    if re.search(r"\b(what|which|how|where|show|give|latest|current|today)\b", lower_message):
        return "en"
    return "de"


def normalize_user_message(user_message: str) -> str:
    if should_assume_magdeburg(user_message):
        note = (
            "Important: If no other place is mentioned, interpret this request as being about Magdeburg."
            if infer_language(user_message) == "en"
            else "Wichtig: Falls kein anderer Ort genannt ist, beziehe diese Anfrage auf Magdeburg."
        )
        return f"{user_message}\n\n{note}"
    return user_message


def should_route_to_rag(user_message: str) -> bool:
    lower_message = user_message.lower()
    return any(keyword in lower_message for keyword in RAG_QUERY_KEYWORDS)


def is_healthcare_proximity_query(user_message: str) -> bool:
    lower_message = user_message.lower()
    health_terms = {
        "doctor", "doctors", "arzt", "ärzte", "practice", "praxen", "pharmacy",
        "pharmacies", "apotheke", "apotheken", "healthcare", "gesundheit",
        "medical", "medizin",
    }
    proximity_terms = {
        "near", "nearby", "closest", "close to", "around", "next to",
        "nahe", "in der nähe", "nähe", "nächste", "naechste", "um",
    }

    has_health_term = any(term in lower_message for term in health_terms)
    has_proximity_term = any(term in lower_message for term in proximity_terms)
    has_address = bool(ADDRESS_PATTERN.search(user_message)) or bool(re.search(r"\b\d{5}\b", user_message))
    return has_health_term and (has_proximity_term or has_address)


def build_healthcare_proximity_unavailable_message(language: str) -> str:
    if language == "en":
        return (
            "I can't reliably find the nearest doctor or pharmacy for a specific address yet. "
            "The current healthcare dataset only contains yearly counts by district for Magdeburg, "
            "not exact provider names, addresses, or coordinates."
        )
    return (
        "Ich kann derzeit nicht zuverlässig den nächstgelegenen Arzt oder die nächstgelegene Apotheke "
        "für eine konkrete Adresse finden. Der aktuelle Gesundheitsdatensatz enthält nur jährliche "
        "Summen nach Stadtteilen für Magdeburg, aber keine genauen Namen, Adressen oder Koordinaten."
    )


def pick_direct_tool(user_message: str) -> tuple[str, dict] | None:
    lower_message = user_message.lower()
    for tool_name, keywords in DIRECT_TOOL_KEYWORDS.items():
        if any(keyword in lower_message for keyword in keywords):
            if tool_name == "energie_klima_trends":
                if "solar" in lower_message or "pv" in lower_message or "photovoltaic" in lower_message:
                    return tool_name, {"thema": "solar"}
                if "led" in lower_message or "streetlight" in lower_message or "streetlights" in lower_message or "street lighting" in lower_message:
                    return tool_name, {"thema": "led"}
                if "energy" in lower_message or "energie" in lower_message or "emissions" in lower_message or "co2" in lower_message:
                    return tool_name, {"thema": "energie"}
                return tool_name, {"thema": "uebersicht"}
            if tool_name == "wirtschaft_trends":
                if "gdp" in lower_message or "bip" in lower_message or "gross value added" in lower_message:
                    return tool_name, {"thema": "bip", "sprache": infer_language(user_message)}
                if "employment" in lower_message or "employed" in lower_message or "jobs" in lower_message or "arbeitsmarkt" in lower_message or "beschäftigung" in lower_message:
                    return tool_name, {"thema": "beschaeftigung", "sprache": infer_language(user_message)}
                if "apprentice" in lower_message or "apprentices" in lower_message or "auszubildende" in lower_message or "ausbildung" in lower_message or "trainee" in lower_message:
                    return tool_name, {"thema": "ausbildung", "sprache": infer_language(user_message)}
                return tool_name, {"thema": "uebersicht", "sprache": infer_language(user_message)}
            if tool_name == "gesundheitsversorgung":
                has_pharmacy = "pharmacy" in lower_message or "pharmacies" in lower_message or "apotheke" in lower_message or "apotheken" in lower_message
                has_rescue = "rescue" in lower_message or "ambulance" in lower_message or "rettungsdienst" in lower_message or "emergency service" in lower_message or "notfall" in lower_message
                has_doctor = "health" in lower_message or "healthcare" in lower_message or "gesundheit" in lower_message or "medical" in lower_message or "medizin" in lower_message or "doctor" in lower_message or "doctors" in lower_message or "arzt" in lower_message or "ärzte" in lower_message or "practice" in lower_message or "praxen" in lower_message
                if has_doctor and has_pharmacy:
                    return tool_name, {"thema": "uebersicht", "sprache": infer_language(user_message)}
                if has_pharmacy:
                    return tool_name, {"thema": "apotheken", "sprache": infer_language(user_message)}
                if has_rescue:
                    return tool_name, {"thema": "rettungsdienst", "sprache": infer_language(user_message)}
                if has_doctor:
                    return tool_name, {"thema": "aerzte", "sprache": infer_language(user_message)}
                return tool_name, {"thema": "uebersicht", "sprache": infer_language(user_message)}
            if tool_name == "mobilitaet_trends":
                if "vehicle fleet" in lower_message or "kraftfahrzeugbestand" in lower_message or "vehicle ownership" in lower_message or "kfz-bestand" in lower_message or "car fleet" in lower_message:
                    return tool_name, {"thema": "fahrzeuge", "sprache": infer_language(user_message)}
                if "ridership" in lower_message or "passenger numbers" in lower_message or "public transport usage" in lower_message or "oepnv entwicklung" in lower_message or "öpnv entwicklung" in lower_message or "fahrgast" in lower_message or "fahrgäste" in lower_message or "passengers transported" in lower_message:
                    return tool_name, {"thema": "oepnv", "sprache": infer_language(user_message)}
                return tool_name, {"thema": "uebersicht", "sprache": infer_language(user_message)}
            if tool_name == "veranstaltungen":
                zeitraum = "heute"
                if "tomorrow" in lower_message or "morgen" in lower_message:
                    zeitraum = "morgen"
                elif "weekend" in lower_message or "wochenende" in lower_message:
                    zeitraum = "wochenende"
                elif "upcoming" in lower_message or "demnächst" in lower_message or "kommende" in lower_message:
                    zeitraum = "bald"

                suchbegriff = ""
                topic_map = {
                    "music": "music",
                    "concert": "music",
                    "konzert": "musik",
                    "musik": "musik",
                    "family": "family",
                    "kids": "kinder",
                    "children": "kinder",
                    "kinder": "kinder",
                    "market": "markt",
                    "flohmarkt": "flohmarkt",
                    "museum": "museum",
                    "exhibition": "ausstellung",
                    "ausstellung": "ausstellung",
                    "sport": "sport",
                }
                for keyword, mapped in topic_map.items():
                    if keyword in lower_message:
                        suchbegriff = mapped
                        break

                return tool_name, {
                    "zeitraum": zeitraum,
                    "suchbegriff": suchbegriff,
                    "sprache": infer_language(user_message),
                }
            return tool_name, {}
    return None


def run_agent(user_message: str, history: list[dict] | None = None) -> str:
    normalized_user_message = normalize_user_message(user_message)
    language = infer_language(user_message)

    if rag_is_configured() and should_route_to_rag(user_message):
        return rag_answer(normalized_user_message, history=history)

    if is_healthcare_proximity_query(user_message):
        return build_healthcare_proximity_unavailable_message(language)

    direct_tool = pick_direct_tool(user_message)
    if direct_tool and ("magdeburg" in user_message.lower() or should_assume_magdeburg(user_message)):
        tool_name, arguments = direct_tool
        return execute_tool(tool_name, arguments)

    provider = get_provider()
    tools = get_tool_schemas()

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if history:
        for msg in history[-6:]:
            if msg.get("role") in ("user", "assistant"):
                messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": normalized_user_message})

    for _ in range(MAX_ITERATIONS):
        result = provider.chat_with_tools(messages, tools)

        if result["type"] == "text":
            return result["content"]

        for tc in result["tool_calls"]:
            tool_result = execute_tool(tc["name"], tc["arguments"])

            messages.append({
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": tc["id"],
                    "type": "function",
                    "function": {
                        "name": tc["name"],
                        "arguments": str(tc["arguments"]),
                    },
                }],
            })
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": tool_result,
            })

    last_text = provider.chat_with_tools(messages, tools=None)
    return last_text.get("content", "Entschuldigung, ich konnte keine Antwort finden.")
