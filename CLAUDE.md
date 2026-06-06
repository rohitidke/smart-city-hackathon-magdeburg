# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MD-Hackathon Smart City Dashboard for Magdeburg, Germany. FastAPI web application with dual-mode AI chat: general LLM conversation and RAG (Retrieval-Augmented Generation) for answering questions about Magdeburg using a curated knowledge base of 54 sources.

**Tech Stack**: Python 3.12+, FastAPI, Qdrant (vector database), Ollama (BGE-M3 embeddings), Jinja2 templates

## Development Commands

### Local Development
```bash
# Install dependencies
uv sync

# Start development server (with hot reload)
uv run uvicorn app.main:app --reload
# → Access at http://127.0.0.1:8000/
```

### Docker
```bash
# Build image
docker build -t md-dashboard .

# Run container
docker run --rm -p 8080:8080 md-dashboard
# → Access at http://127.0.0.1:8080/
```

### RAG System (Local)
```bash
# In data/rag/ directory
docker compose up -d  # Starts Qdrant + Ollama + restores snapshot

# Re-embed documents (if sources.yaml changes)
cd data/rag/embedder
uv sync
uv run python pipeline.py
```

## Environment Configuration

### Required for LLM Chat Mode
- `SERVER_URL` - Remote LLM backend URL (e.g., `https://api.example.com`)
- `SERVER_TOKEN` - Authentication token for LLM backend

### Required for RAG Mode
- `EMBEDDING_URL` - Ollama service URL (default: `http://localhost:11434`)
- `QDRANT_URL` - Vector database URL (default: `http://localhost:6333`)
- `QDRANT_COLLECTION` - Collection name (default: `magdeburg`)

The application gracefully degrades if services are unavailable - chat UI shows status warnings.

## Architecture

### Dual-Mode Chat System

**General Chat Mode**:
```
User Message → POST /api/chat (mode: "chat")
           → app.main.post_llm_chat()
           → HTTP POST to SERVER_URL/api/llm/chat
           → Returns LLM response
```

**RAG Mode**:
```
User Question → POST /api/chat (mode: "rag")
            → app.rag_query.answer()
            → embed(question) via bge-m3
            → Qdrant semantic search (top-k=5)
            → Construct German prompt with:
                - Conversation history (last 6 messages)
                - Retrieved context chunks + source URLs
                - User question
            → post_chat() to LLM backend
            → Returns source-grounded answer
```

### Key Architectural Patterns

1. **Message History Management**: Both modes keep only the **last 8 messages** for token efficiency. RAG mode formats the last 6 messages as conversation context in German (Nutzer: / Assistent:).

2. **Client-Side State**: Conversation histories are maintained separately per mode in [dashboard.html](app/templates/dashboard.html). Switching modes preserves each conversation independently.

3. **German-Language RAG**: RAG prompts and responses are in German. This is critical for Magdeburg context - the LLM is instructed to answer "Antworte nur auf Deutsch" and cite sources.

4. **Source Attribution**: Every RAG response must be grounded in retrieved sources. The system includes source URLs and titles in the prompt, and the LLM is expected to cite them.

5. **External Service Architecture**: The app is stateless and delegates to:
   - Remote LLM backend (shared across deployments)
   - Qdrant (vector database)
   - Ollama (BGE-M3 embeddings, 1024-dim multilingual)

## Critical Files

- [app/main.py](app/main.py) - FastAPI application, routes, chat endpoint, LLM/RAG delegation
- [app/rag_query.py](app/rag_query.py) - Vector search, embedding, German prompt construction, RAG pipeline
- [app/templates/dashboard.html](app/templates/dashboard.html) - Frontend UI, chat logic, mode switching, conversation state
- [data/rag/sources.yaml](data/rag/sources.yaml) - 54 curated Magdeburg sources across 9 categories
- [data/rag/embedder/pipeline.py](data/rag/embedder/pipeline.py) - Document parsing (Docling), chunking (512 tokens), embedding ingestion

## Working with the RAG System

### Knowledge Base Structure
The RAG system indexes 54 documents across 9 categories:
- **Strategie**: ISEK 2030+, Cultural Strategy, Tourism Concept
- **Tourismus**: Travel guides, TouristCard, visit-magdeburg.de
- **Kultur**: Theater, Cathedral, Green Citadel
- **Wikipedia**: Magdeburg articles, Otto von Guericke University
- **Historisch**: City archive, Magdeburg law
- **MMKT**: Tourism board (Magdeburg Marketing)
- **DATEs**: City magazine (events, restaurants)
- **Otto K.**: Otto von Guericke biography
- **Restaurants**: Culinary guides

### Embedding & Search
- **Model**: BGE-M3 (multilingual, 1024-dim vectors)
- **Chunking**: 512-token chunks with overlap (via Docling HybridChunker)
- **Search**: Semantic similarity (top-k=5 chunks)
- **Metadata**: Each chunk includes source URL, title, category

### RAG Response Format
The LLM receives a German prompt structured as:
```
Anleitung: Antworte nur auf Deutsch und nur basierend auf den folgenden Quellen.

Gesprächsverlauf:
Nutzer: [previous question]
Assistent: [previous answer]
...

Kontext:
Quelle: [title] ([url])
[chunk content]
...

Frage: [user question]
```

Responses should cite sources by name/URL. If the answer isn't in the sources, the LLM should say so.

### Modifying the Knowledge Base

1. Edit [data/rag/sources.yaml](data/rag/sources.yaml) (add/remove entries)
2. Place new documents in `data/rag/downloads/`
3. Run embedding pipeline:
   ```bash
   cd data/rag/embedder
   uv run python pipeline.py
   ```
4. Pipeline will download, parse (Docling), chunk, embed (bge-m3), and upsert to Qdrant
5. Create new snapshot (optional):
   ```bash
   # In qdrant container
   curl -X POST http://localhost:6333/collections/magdeburg/snapshots
   ```

## CI/CD

GitHub Actions workflow [.github/workflows/build.yaml](.github/workflows/build.yaml):
1. **Triggers**: Manual workflow dispatch OR push to `main` (if app/, pyproject.toml, Dockerfile, or workflow files change)
2. **Build**: Submits Docker build request to external API
3. **Poll**: Checks build status every 10s (5-minute timeout)
4. **Deploy**: Creates new app revision and polls for deployment (5-minute timeout)
5. **Secrets**: Requires `API_TOKEN` secret and `API_BASE` variable

Deployment is managed by an external build service - not standard Docker registry.

## Data Layer

The [data/](data/) directory contains 14 subdirectories with Magdeburg smart city datasets:
- **Baumkataster**: Tree registry
- **CafesOSM**: Cafes from OpenStreetMap
- **OEV-Daten_NASA_GmbH**: Public transport data
- **Stadtteile**: City districts
- **Unfaelle**: Accident data
- **Zensus**: Census data
- **kiss-md**: KISS Magdeburg data
- **mietspiegel-2024**: Rental market data
- **sensor-data**: Smart city sensor data
- **steuereinnahmen**: Tax revenue data

These datasets are available for future dashboard features but are not currently integrated into the UI or RAG system.
