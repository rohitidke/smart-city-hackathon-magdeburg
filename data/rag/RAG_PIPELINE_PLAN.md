# Magdeburg RAG Pipeline — Phase 2 Design

> Status: **approved, Phase 3 build in progress.**
> Decisions locked: bge-m3 / Qdrant / pre-built snapshot artifact / ISEK 2030+ full PDF + Stadtteile booklet added.
> **Update after approval:** embeddings served via **Ollama** (`ollama pull bge-m3`) — same Ollama instance teams use for chat. Trade-off: Ollama only exposes dense vectors, so the originally-planned hybrid dense+sparse retrieval is **dense-only**. Acceptable for this corpus size / language strength; documented in §5.

This document covers what we will build, why, and the tradeoffs taken. Phase 1 findings are summarised inline only where they drive a decision; the full Phase-1 inventory lives in chat history.

---

## 1. Pipeline at a glance

```
                              docker compose up
                              │
       sources.yaml           │
       downloads/  ───────►  embedder (one-shot worker)
       (54 raw files          │   1. cleanup + dedupe       (Python, Docling SDK)
        + ISEK PDF)           │   2. parse PDFs → DoclingDocument
                              │   3. normalise .txt → DoclingDocument
                              │   4. HybridChunker  ─► chunks + section metadata
                              │   5. bge-m3 embed   ─► dense (1024-d) + sparse
                              │   6. upsert to qdrant
                              ▼
                         qdrant  (single container, persistent volume)
                              │
                              ▼
                  /snapshots/magdeburg_rag_v<N>.snapshot
                              │
                              ▼
                  ── teams clone repo, docker compose up ──
                  Qdrant restores the snapshot → instant retrieval
                  Reference Python / curl examples in README
```

Two-phase compose:
- **`build` profile** — I (you/me) run this once. Worker ingests, Qdrant emits a snapshot, snapshot is published.
- **`run` profile** — teams run this. Qdrant + restored snapshot. No worker, no embedding model on their box. Optional `search-api` sidecar for teams that want a ready-made retrieval endpoint.

---

## 2. Cleanup decisions (Phase 1 carryover)

Codified as a small `cleanup.py` step that runs *before* parsing. Each rule emits to `cleanup_report.json` so the next person can see what got modified.

| Action | Files / sources | Rationale |
|---|---|---|
| **Drop** | `tourismus/md_barrierefrei_2011.pdf` | Server returned HTML; not a PDF. Same accessibility info is in the 2026 48-h brochure. |
| **Drop** | `historisch/urkundenbuch_md_archive.txt` | Trafilatura captured archive.org metadata page, not the book. Optional: re-fetch `https://archive.org/download/urkundenbuchder00hertgoog/urkundenbuchder00hertgoog_djvu.txt` (the full OCR text from the scan). I'll do this if you say yes; otherwise drop. |
| **Dedupe (merge metadata)** | `otto/ottostadt_marke` → `wikipedia/magdeburg_de` | Wikipedia redirect collapsed both. Keep one chunk set, attach both source ids in metadata as a list. |
| **Dedupe (merge metadata)** | `mmkt/mmkt_homepage` ← `mmkt_mediadaten_landing`, `mmkt_ottostadt_marke` | Server returns the same HTML for all three URLs. Same approach: one chunk set, three source ids attached. |
| **Tag low-density** | `strategie/smart_city_landingpage`, `strategie/tourismuskonzept_2030_landing`, `tourismus/magdeburg_tourist_de`, `dates/dates_epaper_landing`, `tourismus/visit_md_landing`, `dates/dates_essen_trinken` | Each is < 1.5 KB usable content. Keep them (citations + grounding) but set `content_density: low` so retrieval layers can deprioritise. |
| **Re-OCR** | `strategie/lsa_digital_2030_md.pdf` | Original was Acrobat-OCR'd in ~2018; visible errors (`Mlnlster!umfUr`). Docling will run EasyOCR over the page images and replace the bad text layer. |
| **Add (manual)** | `strategie/isek_2030_plus.pdf` (full doc) | You'll drop it into `downloads/strategie/` before I run the pipeline. Highest-impact strategic doc; landing page alone is too thin. |

Net result: from 54 nominal sources → ~46 distinct doc clusters with real signal.

---

## 3. Docling: deployment & usage

### Decision: Docling **Python SDK inside the worker container**

```python
from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker
```

### Why not Docling Serve

| | Docling Serve (HTTP service) | Docling SDK in worker (chosen) |
|---|---|---|
| Setup complexity | extra container, HTTP between worker ↔ service | single container, in-process calls |
| Throughput | Designed for many concurrent docs | Sequential is fine: 9 PDFs total, ~30 sec each |
| HybridChunker integration | Need to serialise DoclingDocument across the wire | Same Python process, zero serialisation cost |
| Future "teams parse their own docs" | Easier to expose | Possible but not now — distribution model is a snapshot |
| Container image size | docling-serve image is ~3 GB | Slim Python + pip install docling, ~2 GB |

For a one-shot batch over ~46 sources, the SDK path is clearly simpler. If/when we want teams to ingest their own data live, we add Docling Serve as a separate compose profile — no rework needed.

### Native ARM on M4

Docling pulls `easyocr` + Torch under the hood. We use the `pytorch/pytorch:2.4-arm64` base, **not** `--platform=linux/amd64`. Easier on the fans, faster than QEMU. We pin Docling to ≥ 2.7 (first version with stable HybridChunker API).

---

## 4. Chunking

### Decision: **`HybridChunker` with bge-m3's tokenizer**, ~512 tokens per chunk, ~64-token overlap

```python
chunker = HybridChunker(
    tokenizer="BAAI/bge-m3",
    max_tokens=512,
    overlap_tokens=64,
    merge_peers=True,   # merges short adjacent chunks under the same heading
)
```

### Why HybridChunker over a flat token window

HybridChunker walks the DoclingDocument tree and respects structural boundaries — section headings, list items, table rows, captions. The Phase-1 PDF survey shows why this matters:

- The 48-h brochure has numbered callouts (`1. Erholung`, `2. Action`, `3. Outdoor`). A flat windowing strategy slices these mid-section; HybridChunker keeps each callout intact.
- ISEK and Kulturstrategie have heading hierarchy (`Handlungs-Empfehlung 3` etc.) that becomes section metadata on each chunk → great for source attribution.
- LSA Digital is structured by project (Projekttitel / Zuwendungsempfänger / Förderung / Projektinhalt) — HybridChunker keeps these as coherent blocks.

For the `.txt` files (Wikipedia, HTML extracts), we feed them through Docling's plaintext loader first to get a DoclingDocument; HybridChunker then splits on blank lines / paragraph boundaries.

### Why those numbers

- `max_tokens=512` — bge-m3 supports up to 8192, but multilingual retrieval recall peaks ~256–512 tokens per chunk in practice. Bigger chunks = lower recall, longer prompts.
- `overlap_tokens=64` — small. HybridChunker mostly avoids breaking sentences anyway; overlap is a safety net for the few cases where it must split mid-thought.

### Numbers we expect

| Category | Pre-chunk size (txt + extracted PDF) | Approx chunks |
|---|---|---|
| Wikipedia | ~900 KB across 18 articles | ~450 |
| strategie (incl. ISEK full) | ~3–5 MB across 6 PDFs + landings | ~1,500 |
| tourismus + restaurants | ~6.5 MB (48-h brochure dominates) | ~800 |
| historisch | ~1.5 MB | ~300 |
| kultur, otto, mmkt, dates | ~0.5 MB combined | ~200 |

Rough total: **~3,000–3,500 chunks**, ~10–20 MB of embeddings.

---

## 5. Embedding model: `BAAI/bge-m3`

### Why (already approved, here for completeness)

- Multilingual (100+ languages); strong German performance on MIRACL and BEIR-de
- Dense (1024-d) + native **sparse** (BM25-like) + ColBERT-style multivector in one model
- Apache-2.0 license, no API gating → zero friction for 57 teams
- HuggingFace download once, cached to a volume
- M4 Max via PyTorch MPS: ~150–300 chunks/sec single thread → embedding the full corpus in well under 10 minutes

### Served via Ollama (dense-only)

Ollama hosts bge-m3 via GGUF. Its `/api/embed` endpoint exposes the **dense 1024-d** channel; the native sparse / multivector channels of bge-m3 are not surfaced. We accept this and index dense vectors only:

```python
qdrant.create_collection(
    "magdeburg",
    vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
)
```

The cost: rare-token queries ("Wasserstraßenkreuz", "Hundertwasserhaus") rely on the dense channel to match; they would have benefited from sparse fusion. The benefit: one inference service (Ollama) instead of two stacks (Ollama for chat + FlagEmbedding+Torch in the worker), which matters when shipping a clean compose to 57 teams.

### Alternatives considered (declined)

- `multilingual-e5-large` — clean, smaller (560M), but no native sparse vectors. Fine pick if hybrid feels like overengineering.
- `jina-embeddings-v3` — strong but recommends API-side inference; less battle-tested locally.
- watsonx `slate-125m-multilingual` — kills the "no API keys for participants" property. Out.

---

## 6. Vector store: **Qdrant 1.12+**

### Collection layout

```python
client.create_collection(
    collection_name="magdeburg",
    vectors_config={
        "dense": VectorParams(size=1024, distance=Distance.COSINE),
    },
    sparse_vectors_config={
        "sparse": SparseVectorParams(modifier=Modifier.IDF),
    },
    on_disk_payload=True,  # keep payload on disk, vectors in RAM
)
```

Payload indexes for fast filtering:
```python
client.create_payload_index("magdeburg", "category", "keyword")
client.create_payload_index("magdeburg", "source_id", "keyword")
client.create_payload_index("magdeburg", "format", "keyword")
client.create_payload_index("magdeburg", "content_density", "keyword")
```

### Why Qdrant for this use case

- Single binary / single container; ARM64 native build → fast on M4
- REST (6333) + gRPC (6334); teams can hit either or use the official Python / TS clients
- **Snapshots** are first-class: `POST /collections/<name>/snapshots` produces a `.snapshot` file we can ship as the distribution artifact
- Payload filtering is exactly what hackathon teams need ("only category=restaurants")

Chroma was the alternative — it would work for one laptop, but operational story is weaker (single-process file-backed). For 57 teams who'll plug Qdrant into LangChain / LlamaIndex / direct REST, Qdrant is the more professional handoff.

---

## 7. Metadata schema (per chunk)

Stored as the Qdrant payload. JSON-serialisable, flat where possible to keep filtering ergonomic.

```jsonc
{
  // Identifier
  "chunk_id":        "sha256(source_id + chunk_index + text)",  // deterministic → idempotent upsert
  "chunk_index":     7,                          // position within the source doc

  // Source attribution (from sources.yaml)
  "source_id":       "isek_2030_plus",
  "source_id_alt":   ["ottostadt_marke"],        // for merged duplicates; usually []
  "category":        "strategie",
  "title":           "Integriertes Stadtentwicklungskonzept ISEK 2030+",
  "source_url":      "https://www.magdeburg.de/...",
  "format":          "pdf",                      // pdf | html | wikipedia

  // Layout-aware fields (from Docling)
  "page_number":     12,                         // PDF only; null otherwise
  "section_path":    ["Kapitel 4", "Mobilität", "Radverkehr"],   // breadcrumb of headings

  // Curation flags
  "content_density": "high",                     // high | medium | low
  "language":        "de",                       // "de" | "en" (one EN Wikipedia article + EN Otto)
  "license":         "cc-by-sa-3.0",             // mostly Wikipedia + city-CMS

  // Bookkeeping
  "ingested_at":     "2026-05-25T...Z",
  "pipeline_version": "v1.0.0",

  // The actual chunk text
  "text":            "..."
}
```

`section_path` is the secret sauce for good attribution — teams can show the user not just "from ISEK 2030+" but "from ISEK 2030+ → Mobilität → Radverkehr".

`chunk_id` being a content hash means re-running the pipeline on the same corpus produces the same ids → safe upsert, no duplicates after a refresh.

---

## 8. Distribution: prebuilt snapshot artifact

```
# pipeline build (one-time, done by us)
docker compose --profile build up --build
# → Qdrant container POSTs /collections/magdeburg/snapshots
# → result: snapshots/magdeburg_rag_v1.snapshot  (~30–80 MB gzipped)

# publish
gh release create magdeburg-rag-v1 snapshots/magdeburg_rag_v1.snapshot.tar.gz

# teams
git clone <repo>
cd <repo>
make download-snapshot     # or just `docker compose up` if snapshot is bundled in image
docker compose up
# Qdrant restores the snapshot on boot; collection is queryable in seconds
```

### Why prebuilt over rebuild-on-first-run

- Reproducibility: every team queries the exact same corpus, same chunk boundaries, same vectors. Pitches are comparable.
- Spin-up time: 30 seconds to a working Qdrant vs. ~10–30 minutes of model download + parse + embed × 57 laptops.
- Hackathon-day failure surface: zero PDF parsing happens on the participant's machine, so heavy PDFs / OCR can't hose anyone's setup.

### Versioning

`pipeline_version` in payload + `magdeburg_rag_v<N>.snapshot` filename. If we refresh post-event (e.g. you get the MMKT Mediadaten 2026 PDF), it's a clean v2 with all chunk_ids deterministic from content → diffable.

### Size estimate

3,500 chunks × (1024-d float32 + ~1 KB payload + sparse vector ~50 nonzeros) ≈ **20–40 MB** uncompressed Qdrant collection. Snapshot compresses well; expect ~15–30 MB on disk for the release artifact. Fits comfortably in a GitHub Release asset.

---

## 9. Compose architecture

```yaml
# compose.yaml (sketch — full version comes in Phase 3)
name: magdeburg-rag

services:
  qdrant:
    image: qdrant/qdrant:v1.12.4
    ports: ["6333:6333", "6334:6334"]
    volumes:
      - qdrant_storage:/qdrant/storage
      - ./snapshots:/qdrant/snapshots

  ollama:
    image: ollama/ollama:latest
    ports: ["11434:11434"]
    volumes:
      - ollama_models:/root/.ollama

  # --- BUILD-ONLY (one-shot worker) ---
  embedder:
    profiles: ["build"]
    build: ./embedder
    depends_on: { qdrant: ..., ollama: ... }
    volumes:
      - ./downloads:/data/downloads:ro
      - ./sources.yaml:/data/sources.yaml:ro
      - ./snapshots:/snapshots
      - hf_cache:/root/.cache/huggingface
    environment:
      QDRANT_URL: http://qdrant:6333
      OLLAMA_URL: http://ollama:11434
      EMBED_MODEL: bge-m3
      COLLECTION_NAME: magdeburg

volumes:
  qdrant_storage:
  ollama_models:
  hf_cache:
```

No `search-api` sidecar — teams are using Ollama directly for both chat and embeddings, so they can hit Qdrant + Ollama directly from their app. We provide curl + Python query examples in `HACKATHON_README.md`.

Teams who already run Ollama on the host can override the port (`OLLAMA_PORT=11435 docker compose up`) or comment out the `ollama` service to use their host install via `host.docker.internal`.

---

## 10. Idempotency & re-runs

- `chunk_id = sha256(f"{source_id}::{chunk_index}::{normalized_text}")`
- Worker pulls existing chunk_ids for the collection on startup, computes the new set, upserts the diff
- A source whose text changes → different chunk_ids → old ones become orphans → optional `--prune` flag cleans them
- `cleanup_report.json` + a CLI flag `--dry-run` make refreshes safe to inspect before they touch Qdrant

---

## 11. Sanity-check protocol (end of Phase 3)

I'll run these 5 queries against the built collection and paste top-5 hits with source attribution into chat so you can judge retrieval quality before we hand off:

1. *"Welche Strategie verfolgt Magdeburg im Tourismus?"* — expect ISEK / Tourismuskonzept 2030 / MMKT
2. *"Wann wurde Magdeburg gegründet?"* — expect Magdeburg DE / Geschichte / Magdeburger Recht
3. *"Wo kann ich in Magdeburg vegan essen?"* — expect visit_md_kulinarik / DATEs / 48-h brochure (gastronomy section)
4. *"Was war die Magdeburger Hochzeit 1631?"* — expect zerstoerung_md_1631 / Festung / Geschichte
5. *"Welche Smart-City-Projekte werden in Magdeburg gefördert?"* — expect LSA Digital 2030 / Smart Cities Merkblatt / Smart City Landing

If any of these returns garbage in the top-3, we iterate (chunk size, hybrid weights, OCR re-run on stragglers) before declaring victory.

---

## 12. Known risks / open questions

| Risk | Mitigation |
|---|---|
| LSA Digital re-OCR doesn't beat the embedded text | Fall back to the existing text layer; OCR errors only hurt the LSA chunks, not the whole corpus. |
| bge-m3 first-download (~2 GB) flakes on hackathon WiFi | Bake the model into the snapshot image OR vendor it as part of the GitHub Release. |
| Snapshot restore fails for teams on weird storage drivers | Provide a `--rebuild` escape hatch in the compose stack that runs the `build` profile end-to-end. ~30 min on first run, but no hard dependency on snapshot semantics. |
| Wikipedia content shifts post-embed | Pin `ingested_at` and the Wikipedia revision id in payload (cheap; one extra MediaWiki API field). |

### Open question for you

1. **Ship the `search-api` sidecar, or just Qdrant?** I'd ship it (~150 lines of FastAPI, zero dependencies for teams who use it, ignorable for teams who don't). But if you'd rather keep the deliverable to "raw Qdrant + a README with curl examples", that's fine too — leaner artifact, no maintenance surface.
2. **Re-fetch the Urkundenbuch's actual OCR text** via archive.org's `_djvu.txt` endpoint? It's ~5 MB of 19th-century Latin/German charter text — possibly noisy for RAG, possibly Gold for a "Magdeburger Recht" deep-dive. Cheap to add; low-confidence value.

---

## Phase 3 deliverables (what gets built once approved)

- `cleanup.py` — applies the §2 cleanup rules, emits `cleanup_report.json`
- `embedder/` — Docker context: `Dockerfile`, `pipeline.py` (parse → chunk → embed → upsert)
- `search-api/` — FastAPI sidecar (if approved)
- `compose.yaml` — build + run profiles per §9
- `snapshots/magdeburg_rag_v1.snapshot.tar.gz` — the artifact
- `HACKATHON_README.md` — 1-pager for the 57 teams: clone, compose up, example queries, how to cite sources
- Retrieval sanity-check output pasted in chat per §11

Estimated build time: 1 working session, plus model-download + embed wall time.
