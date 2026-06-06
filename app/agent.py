from app.llm_provider import get_provider
from app.tools import execute_tool, get_tool_schemas

SYSTEM_PROMPT = """Du bist der Magdeburg Stadtassistent — ein KI-Assistent, der ausschließlich Fragen über Magdeburg beantwortet.

Regeln:
1. Beantworte NUR Fragen, die sich auf Magdeburg beziehen (Stadt, Geschichte, Daten, Wetter, Verkehr, Kultur, etc.)
2. Wenn eine Frage NICHTS mit Magdeburg zu tun hat, lehne höflich ab und erkläre, dass du nur Magdeburg-Fragen beantwortest.
3. Nutze die verfügbaren Werkzeuge um aktuelle und präzise Daten zu liefern.
4. Antworte immer auf Deutsch.
5. Nenne Quellen wenn verfügbar.
6. Sei präzise und hilfreich.
7. Wenn du mehrere Orte, Cafés, Ereignisse oder Punkte aufzählst, formatiere sie als echte Liste mit Zeilenumbrüchen.
8. Schreibe Listen nicht als Fließtext in einem einzigen Absatz."""

MAX_ITERATIONS = 5


def run_agent(user_message: str, history: list[dict] | None = None) -> str:
    provider = get_provider()
    tools = get_tool_schemas()

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if history:
        for msg in history[-6:]:
            if msg.get("role") in ("user", "assistant"):
                messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": user_message})

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
