import os

import requests
from qdrant_client import QdrantClient

EMBEDDING_URL = os.getenv("EMBEDDING_URL", "http://localhost:11434")
qdrant = QdrantClient(url="http://localhost:6333")


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
        collection_name="magdeburg",
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


def answer(question: str, k: int = 5):
    hits = search(question, k=k)
    context = "\n\n".join(
        f"[Quelle: {h.payload['title']} — {h.payload['source_url']}]\n{h.payload['text']}"
        for h in hits
    )
    prompt = f"""Beantworte die Frage auf Deutsch. Stütze dich AUSSCHLIESSLICH
auf die folgenden Quellen. Wenn die Quellen die Frage nicht beantworten,
sage das ehrlich. Nenne am Ende die genutzten Quellen.

Quellen:
{context}

Frage: {question}
Antwort:"""
    return post_chat(prompt)


if __name__ == "__main__":
    print(answer("Welche Smart-City-Projekte werden in Magdeburg gefördert?",2))
