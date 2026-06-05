#!/usr/bin/env python3
"""
Magdeburg RAG embedding pipeline.

Reads sources.yaml + downloads/, applies cleanup rules, parses with Docling,
chunks with HybridChunker, embeds via Ollama (bge-m3), upserts into Qdrant,
and triggers a snapshot.

Designed as a one-shot worker (compose profile=build). Idempotent: chunk_ids
are content hashes, so a re-run upserts the same ids without duplication.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
import tempfile
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import requests
import yaml
from docling.chunking import HybridChunker
from docling.document_converter import DocumentConverter
from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    PointStruct,
    VectorParams,
    PayloadSchemaType,
)
from transformers import AutoTokenizer

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s  %(levelname)-7s  %(name)s  %(message)s",
)
log = logging.getLogger("pipeline")

DATA_ROOT = Path(os.environ.get("DATA_ROOT", "/data"))
DOWNLOADS = DATA_ROOT / "downloads"
SOURCES_YAML = DATA_ROOT / "sources.yaml"
SNAPSHOT_DIR = Path(os.environ.get("SNAPSHOT_OUT", "/snapshots"))

QDRANT_URL = os.environ.get("QDRANT_URL", "http://qdrant:6333")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "bge-m3")
COLLECTION = os.environ.get("COLLECTION_NAME", "magdeburg")
PIPELINE_VERSION = os.environ.get("PIPELINE_VERSION", "v1.0.0")

# bge-m3 vector dim
VECTOR_SIZE = 1024
# chunking budget — fits well below bge-m3's 8192 limit while keeping recall up
MAX_TOKENS = 512
# Wikipedia articles tag chunks as "high"; CMS landing pages as "low".
LOW_DENSITY_SOURCES = {
    "smart_city_landingpage",
    "tourismuskonzept_2030_landing",
    "magdeburg_tourist_de",
    "dates_epaper_landing",
    "visit_md_landing",
    "dates_essen_trinken",
    "dates_veranstaltungen",
}
# Sources to drop entirely (broken extractions identified in Phase 1).
DROP_SOURCES = {
    "md_barrierefrei_2011",  # server returned HTML, not PDF
    "urkundenbuch_md_archive",  # trafilatura captured archive.org metadata only
}
# Sources that produced byte-identical content via Wikipedia/server redirect.
# Map: duplicate source_id → canonical source_id whose chunks we keep.
DUPLICATE_OF = {
    "ottostadt_marke": "magdeburg_de",
    "mmkt_mediadaten_landing": "mmkt_homepage",
    "mmkt_ottostadt_marke": "mmkt_homepage",
}


@dataclass
class Source:
    category: str
    id: str
    title: str
    url: str
    format: str  # pdf | html | wikipedia
    note: str = ""

    def file_path(self) -> Path | None:
        """Return the on-disk file for this source, or None if missing."""
        cat = DOWNLOADS / self.category
        if self.format == "pdf":
            p = cat / f"{self.id}.pdf"
        else:  # html | wikipedia
            p = cat / f"{self.id}.txt"
        return p if p.exists() else None


@dataclass
class CleanupReport:
    dropped: list[dict] = field(default_factory=list)
    merged: list[dict] = field(default_factory=list)
    tagged_low_density: list[str] = field(default_factory=list)
    missing_files: list[dict] = field(default_factory=list)


def load_sources() -> list[Source]:
    raw = yaml.safe_load(SOURCES_YAML.read_text(encoding="utf-8"))
    out: list[Source] = []
    for cat, items in raw.items():
        for it in items:
            out.append(
                Source(
                    category=cat,
                    id=it["id"],
                    title=it["title"],
                    url=it["url"],
                    format=it["format"],
                    note=it.get("note", "").strip(),
                )
            )
    return out


def apply_cleanup(sources: list[Source]) -> tuple[list[Source], CleanupReport]:
    """Apply Phase-1 cleanup rules. Returns the surviving sources + a report."""
    report = CleanupReport()

    survivors: list[Source] = []
    # First pass: build a duplicate_groups map so canonicals know their aliases
    alias_map: dict[str, list[str]] = {}
    for dup, canonical in DUPLICATE_OF.items():
        alias_map.setdefault(canonical, []).append(dup)

    for s in sources:
        # Drop policy
        if s.id in DROP_SOURCES:
            report.dropped.append({"id": s.id, "reason": "broken extraction"})
            continue

        # Skip duplicates of canonicals (we'll attach their ids to canonical's payload)
        if s.id in DUPLICATE_OF:
            report.merged.append(
                {"id": s.id, "merged_into": DUPLICATE_OF[s.id]}
            )
            continue

        # Skip the kultur dup of kulturstrategie (already covered under strategie)
        if s.id == "kulturstrategie_2030_dup":
            report.merged.append(
                {"id": s.id, "merged_into": "kulturstrategie_2030"}
            )
            continue

        # File presence check
        f = s.file_path()
        if f is None:
            report.missing_files.append({"id": s.id, "category": s.category})
            continue

        if s.id in LOW_DENSITY_SOURCES:
            report.tagged_low_density.append(s.id)

        survivors.append(s)

    return survivors, report


# ---------- Docling / chunking ----------

_converter: DocumentConverter | None = None


def converter() -> DocumentConverter:
    global _converter
    if _converter is None:
        log.info("loading Docling DocumentConverter (first call cold-starts ML models)")
        _converter = DocumentConverter()
    return _converter


def to_docling_document(source: Source):
    """Convert a source file to a DoclingDocument.

    PDFs go through the layout-aware converter. .txt files (Wikipedia +
    HTML extracts) are fed as markdown — they already have a `# Title` header
    line and clean paragraph structure from the upstream extractor.
    """
    path = source.file_path()
    if path is None:
        raise FileNotFoundError(path)

    if source.format == "pdf":
        result = converter().convert(str(path))
        return result.document

    # .txt path: write to a temp .md file so DocumentConverter picks the
    # markdown backend; this gives us paragraph + heading structure.
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(path.read_text(encoding="utf-8"))
        tmp_path = tmp.name
    try:
        result = converter().convert(tmp_path)
        return result.document
    finally:
        os.unlink(tmp_path)


def make_chunker() -> HybridChunker:
    log.info("loading bge-m3 tokenizer (for chunking budget only — no model weights)")
    tokenizer = AutoTokenizer.from_pretrained("BAAI/bge-m3")
    return HybridChunker(
        tokenizer=tokenizer,
        max_tokens=MAX_TOKENS,
        merge_peers=True,
    )


# ---------- Ollama embedding ----------


def ensure_ollama_model(model: str) -> None:
    """Pull the embedding model if it isn't already loaded."""
    r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=10)
    r.raise_for_status()
    have = {m["name"].split(":")[0] for m in r.json().get("models", [])}
    if model.split(":")[0] in have:
        log.info("ollama: %s already pulled", model)
        return
    log.info("ollama: pulling %s (this is a one-time download)", model)
    with requests.post(
        f"{OLLAMA_URL}/api/pull", json={"name": model, "stream": True}, stream=True, timeout=None
    ) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines():
            if not line:
                continue
            evt = json.loads(line)
            if "status" in evt and ("pulling" not in evt["status"]):
                log.info("ollama pull: %s", evt["status"])
    log.info("ollama: pull complete")


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a batch via Ollama. Ollama supports `input` as a list."""
    r = requests.post(
        f"{OLLAMA_URL}/api/embed",
        json={"model": EMBED_MODEL, "input": texts},
        timeout=300,
    )
    r.raise_for_status()
    data = r.json()
    embs = data.get("embeddings") or [data.get("embedding")]
    if not embs or any(e is None for e in embs):
        raise RuntimeError(f"ollama returned no embeddings: {data}")
    return embs


# ---------- Qdrant ----------


def setup_qdrant() -> QdrantClient:
    client = QdrantClient(url=QDRANT_URL, timeout=60)
    # Wait for ready
    for _ in range(60):
        try:
            client.get_collections()
            break
        except Exception:
            time.sleep(1)
    else:
        raise RuntimeError("Qdrant not ready after 60s")

    if client.collection_exists(COLLECTION):
        log.info("qdrant: collection %s already exists — recreating fresh", COLLECTION)
        client.delete_collection(COLLECTION)

    client.create_collection(
        collection_name=COLLECTION,
        vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
    )
    for field_name, schema in [
        ("category", PayloadSchemaType.KEYWORD),
        ("source_id", PayloadSchemaType.KEYWORD),
        ("format", PayloadSchemaType.KEYWORD),
        ("content_density", PayloadSchemaType.KEYWORD),
        ("language", PayloadSchemaType.KEYWORD),
    ]:
        client.create_payload_index(COLLECTION, field_name, schema)
    log.info("qdrant: collection %s created with payload indexes", COLLECTION)
    return client


def chunk_id_for(source_id: str, idx: int, text: str) -> str:
    h = hashlib.sha256(f"{source_id}::{idx}::{text}".encode("utf-8")).hexdigest()
    return h[:32]  # 128 bits, fits Qdrant uuid-style point id


def chunk_id_to_int(chunk_id_hex: str) -> int:
    # Qdrant point ids must be int or uuid. We give it a deterministic int from hash.
    return int(chunk_id_hex[:15], 16)


# ---------- Main pipeline ----------


def section_path(meta) -> list[str]:
    """Extract section breadcrumb from a Docling chunk's meta."""
    # Docling 2.x: chunk.meta.headings is a list of heading strings up the tree.
    headings = getattr(meta, "headings", None) or []
    return [h for h in headings if h]


def doc_language(source: Source) -> str:
    if source.id.endswith("_en") or source.url.startswith("https://en."):
        return "en"
    return "de"


def doc_license(source: Source) -> str:
    if "wikipedia.org" in source.url:
        return "cc-by-sa-3.0"
    if "magdeburg.de" in source.url or "magdeburg-tourist.de" in source.url:
        return "source-website"
    if "kfw.de" in source.url:
        return "source-website"
    if "uni-flensburg.de" in source.url:
        return "source-website"
    if "visit-magdeburg.de" in source.url:
        return "source-website"
    return "source-website"


def run() -> int:
    log.info("pipeline %s starting", PIPELINE_VERSION)

    sources_all = load_sources()
    log.info("loaded %d source entries from sources.yaml", len(sources_all))

    sources, cleanup = apply_cleanup(sources_all)
    log.info(
        "cleanup: %d sources survive (%d dropped, %d merged into canonicals, %d missing files)",
        len(sources),
        len(cleanup.dropped),
        len(cleanup.merged),
        len(cleanup.missing_files),
    )

    # Build aliases lookup for canonical sources
    alias_map: dict[str, list[str]] = {}
    for dup, canonical in DUPLICATE_OF.items():
        alias_map.setdefault(canonical, []).append(dup)

    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    (SNAPSHOT_DIR / "cleanup_report.json").write_text(
        json.dumps(
            {
                "dropped": cleanup.dropped,
                "merged": cleanup.merged,
                "tagged_low_density": cleanup.tagged_low_density,
                "missing_files": cleanup.missing_files,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    ensure_ollama_model(EMBED_MODEL)
    chunker = make_chunker()
    qclient = setup_qdrant()

    total_chunks = 0
    now_iso = datetime.now(timezone.utc).isoformat()

    for s in sources:
        path = s.file_path()
        log.info("→ %s/%s  (%s, %s)", s.category, s.id, s.format, path.name)
        try:
            doc = to_docling_document(s)
        except Exception as e:
            log.error("parse failed for %s: %s", s.id, e)
            continue

        try:
            chunks = list(chunker.chunk(doc))
        except Exception as e:
            log.error("chunking failed for %s: %s", s.id, e)
            continue

        if not chunks:
            log.warning("  no chunks produced for %s", s.id)
            continue

        texts = [chunker.contextualize(c) for c in chunks]
        # Batched embedding
        BATCH = 32
        vecs: list[list[float]] = []
        for i in range(0, len(texts), BATCH):
            vecs.extend(embed_batch(texts[i : i + BATCH]))

        # Build points
        points: list[PointStruct] = []
        density = "low" if s.id in LOW_DENSITY_SOURCES else "high"
        lang = doc_language(s)
        lic = doc_license(s)
        aliases = alias_map.get(s.id, [])

        for idx, (chunk, text, vec) in enumerate(zip(chunks, texts, vecs)):
            cid_hex = chunk_id_for(s.id, idx, text)
            page = None
            # Docling exposes provenance per chunk; first prov item's page_no when known
            try:
                provs = chunk.meta.doc_items[0].prov if chunk.meta.doc_items else []
                if provs:
                    page = getattr(provs[0], "page_no", None)
            except Exception:
                page = None

            payload = {
                "chunk_index": idx,
                "source_id": s.id,
                "source_id_alt": aliases,
                "category": s.category,
                "title": s.title,
                "source_url": s.url,
                "format": s.format,
                "page_number": page,
                "section_path": section_path(chunk.meta),
                "content_density": density,
                "language": lang,
                "license": lic,
                "ingested_at": now_iso,
                "pipeline_version": PIPELINE_VERSION,
                "text": text,
            }
            points.append(
                PointStruct(id=chunk_id_to_int(cid_hex), vector=vec, payload=payload)
            )

        qclient.upsert(collection_name=COLLECTION, points=points, wait=True)
        total_chunks += len(points)
        log.info("  %d chunks upserted (running total: %d)", len(points), total_chunks)

    log.info("embedding complete: %d chunks across %d sources", total_chunks, len(sources))

    # Snapshot
    snap = qclient.create_snapshot(collection_name=COLLECTION)
    log.info("snapshot created: %s", snap.name)
    # Snapshot file lives at /qdrant/snapshots in the qdrant container,
    # mounted at SNAPSHOT_DIR here too.
    log.info("snapshot path (on host): %s/%s/%s", SNAPSHOT_DIR, COLLECTION, snap.name)

    return 0


if __name__ == "__main__":
    sys.exit(run())
