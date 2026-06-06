import os

import requests
from qdrant_client import QdrantClient

import app.env  # noqa: F401

EMBEDDING_URL = os.getenv("EMBEDDING_URL", "http://localhost:11434")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_COLLECTION = os.getenv("QDRANT_COLLECTION", "magdeburg")

qdrant = QdrantClient(url=QDRANT_URL)


def embed(text: str) -> list[float]:
    r = requests.post(f"{EMBEDDING_URL}/api/embed",
                      json={"model": "bge-m3", "input": text}, timeout=30)
    r.raise_for_status()
    return r.json()["embeddings"][0]


def search(question: str, k: int = 5, category: str | None = None):
    from qdrant_client.http.models import Filter, FieldCondition, MatchValue
    flt = None
    if category:
        flt = Filter(must=[FieldCondition(key="category",
                                          match=MatchValue(value=category))])
    return qdrant.query_points(
        collection_name=QDRANT_COLLECTION,
        query=embed(question),
        query_filter=flt,
        limit=k,
        with_payload=True,
    ).points

# for hit in search("Welche Smart-City-Projekte werden in Magdeburg gefördert?"):
#     p = hit.payload
#     print(f"[{hit.score:.3f}] {p['title']}  →  {p['source_url']}")
#     print(f"        {p['text'][:160].strip()}…\n")


def get_server_config() -> tuple[str, str]:
    server_url = os.getenv("SERVER_URL")
    server_token = os.getenv("SERVER_TOKEN")
    if not server_url or not server_token:
        raise RuntimeError(
            "Set SERVER_URL and SERVER_TOKEN to use the remote /api/llm/chat endpoint."
        )
    return server_url.rstrip("/"), server_token


def rag_is_configured() -> bool:
    return bool(
        os.getenv("SERVER_URL")
        and os.getenv("SERVER_TOKEN")
        and EMBEDDING_URL
        and QDRANT_URL
        and QDRANT_COLLECTION
    )


def post_chat(prompt: str) -> str:
    server_url, server_token = get_server_config()
    r = requests.post(
        f"{server_url}/api/llm/chat",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {server_token}",
        },
        json={"messages": [{"role": "user", "content": prompt}]},
        timeout=120,
    )
    r.raise_for_status()
    data = r.json()
    response = data.get("response")
    if not isinstance(response, str):
        raise RuntimeError("LLM backend returned an unexpected response format.")
    return response


def format_history(messages: list[dict[str, str]] | None) -> str:
    if not messages:
        return ""

    history_lines = []
    for message in messages[-6:]:
        role = message.get("role")
        content = message.get("content", "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        speaker = "Nutzer" if role == "user" else "Assistent"
        history_lines.append(f"{speaker}: {content}")
    return "\n".join(history_lines)


def answer(question: str, k: int = 5, history: list[dict[str, str]] | None = None):
    hits = search(question, k=k)
    context = "\n\n".join(
        f"[Quelle: {h.payload['title']} — {h.payload['source_url']}]\n{h.payload['text']}"
        for h in hits
    )
    conversation_history = format_history(history)
    prompt = f"""Beantworte die Frage in derselben Sprache wie die Frage des Nutzers
(Deutsch oder Englisch). Stütze dich AUSSCHLIESSLICH auf die folgenden Quellen.
Wenn die Quellen die Frage nicht beantworten, sage das ehrlich.
Nenne am Ende die genutzten Quellen.
Wenn du mehrere Punkte aufzählst, formatiere sie als Markdown-Liste mit Bindestrichen und Zeilenumbrüchen.
Schreibe dabei jeden Punkt im Format `- **Titel**` und die Erläuterung in den folgenden Zeilen.

Bisherige Unterhaltung:
{conversation_history or "Keine vorherige Unterhaltung."}

Quellen:
{context}

Frage: {question}
Antwort:"""
    return post_chat(prompt)


if __name__ == "__main__":
    print(answer("Welche Smart-City-Projekte werden in Magdeburg gefördert?",2))
