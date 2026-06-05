#!/usr/bin/env python3
"""Run a handful of sanity-check queries against the freshly-built collection."""
import os
import textwrap

import requests
from qdrant_client import QdrantClient

QDRANT = os.environ.get("QDRANT_URL", "http://qdrant:6333")
OLLAMA = os.environ.get("OLLAMA_URL", "http://ollama:11434")
COLL = "magdeburg"

client = QdrantClient(url=QDRANT, timeout=30)


def embed(text: str) -> list[float]:
    r = requests.post(f"{OLLAMA}/api/embed", json={"model": "bge-m3", "input": text}, timeout=60)
    r.raise_for_status()
    return r.json()["embeddings"][0]


def show(question: str, k: int = 5):
    print("=" * 88)
    print(f"Q: {question}")
    print("-" * 88)
    hits = client.query_points(
        collection_name=COLL, query=embed(question), limit=k, with_payload=True
    ).points
    for i, h in enumerate(hits, 1):
        p = h.payload
        sp = " › ".join(p.get("section_path") or [])
        page = p.get("page_number")
        loc = f"p.{page}" if page else ""
        snippet = " ".join(p["text"].split())[:200]
        print(f"  [{i}] score={h.score:.3f}  {p['source_id']}  ({p['category']}) {loc}")
        if sp:
            print(f"      ↳ {sp}")
        print(f"      {textwrap.fill(snippet, 86, subsequent_indent='      ')}…")
    print()


for q in [
    "Welche Strategie verfolgt Magdeburg im Tourismus?",
    "Wann wurde Magdeburg gegründet?",
    "Wo kann ich in Magdeburg vegan oder vegetarisch essen?",
    "Was war die Magdeburger Hochzeit 1631?",
    "Welche Smart-City-Projekte werden in Magdeburg gefördert?",
]:
    show(q, k=5)
