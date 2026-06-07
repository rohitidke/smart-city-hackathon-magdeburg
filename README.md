# Smart City Magdeburg

A FastAPI-based smart city dashboard and AI assistant for exploring Magdeburg through open data, live city information, and optional retrieval-augmented generation (RAG).

The project combines:

- interactive dashboard pages for key city topics
- a Magdeburg-only AI assistant with tool calling
- local datasets for housing, mobility, environment, health, economy, and demographics
- optional document search over curated city sources

If someone opens this repository on GitHub, they should quickly understand one thing: this app helps people explore and ask questions about **Magdeburg** using both structured data and AI.

## What This Project Does

This application is designed as a city intelligence interface for Magdeburg. It gives users two ways to explore the city:

1. Browse dashboard pages with curated KPIs and topic summaries.
2. Ask natural-language questions in German or English.

The assistant is intentionally scoped to Magdeburg. It can answer questions about topics such as:

- weather and air quality
- rent and housing
- public transport and mobility
- economy and tax trends
- healthcare coverage
- trees, climate, and environmental indicators
- demographics and quality of life
- Magdeburg-specific documents via RAG

## Main Features

| Feature | Description |
| --- | --- |
| Dashboard UI | Multi-page FastAPI + Jinja interface for city categories such as environment, mobility, living, economy, and quality of life |
| AI Chat Assistant | Tool-using city assistant that answers only Magdeburg-related questions |
| Bilingual Support | Responds in German or English based on the user's message |
| Local Data Processing | Loads GeoJSON, CSV, and JSON datasets from the repository |
| Live Data Tools | Can fetch current weather, water level, air quality, and Magdeburg-specific web results |
| Optional RAG | Searches curated Magdeburg documents stored in Qdrant with external embeddings |

## Pages

After starting the app, these routes are available:

- `/` - landing page with overview KPIs
- `/chat` - AI assistant
- `/environment` - environment and climate
- `/mobility` - mobility and safety
- `/living` - housing and living
- `/economy` - economy and finance
- `/quality` - quality of life
- `/demographics` - population and demographic view

## Tech Stack

- Python 3.12
- FastAPI
- Jinja2 templates
- Uvicorn
- `uv` for dependency management
- OpenAI-compatible LLM integration
- Optional Qdrant-based RAG pipeline

## Project Structure

```text
app/
  main.py              FastAPI entrypoint and routes
  agent.py             Magdeburg-scoped tool-calling assistant
  llm_provider.py      OpenAI / remote LLM provider abstraction
  rag_query.py         RAG search + answer flow
  tools/               Domain tools for weather, rent, mobility, tax, etc.
  templates/           Jinja templates for the frontend
  static/              CSS, JS, icons, and prepared chart data

data/
  kiss-md/             City datasets
  rag/                 Curated RAG sources and pipeline assets
  sensor-data/         Climate and sensor exports
  steuereinnahmen/     Tax revenue datasets
  ...                  Additional city-specific data sources
```

## Quick Start

### 1. Prerequisites

Make sure you have:

- Python 3.12+
- `uv` installed: <https://docs.astral.sh/uv/>

### 2. Install dependencies

```bash
uv sync
```

### 3. Create a `.env` file

The app automatically loads environment variables from a `.env` file in the repository root.

Minimal OpenAI-based setup:

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
```

Optional OpenAI-compatible base URL:

```env
OPENAI_BASE_URL=https://eu.api.openai.com/v1
```

Alternative remote LLM backend setup:

```env
SERVER_URL=https://your-server.example.com
SERVER_TOKEN=your_token
```

Optional RAG setup:

```env
EMBEDDING_URL=http://localhost:11434
QDRANT_URL=http://localhost:6333
QDRANT_COLLECTION=magdeburg
```

### 4. Run the app

```bash
uv run uvicorn app.main:app --reload
```

### 5. Open it in the browser

```text
http://127.0.0.1:8000/
```

## Configuration Notes

| Variable | Required | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | Yes, unless using `SERVER_URL` + `SERVER_TOKEN` | Enables the OpenAI provider |
| `OPENAI_MODEL` | No | Defaults to `gpt-4o-mini` |
| `OPENAI_BASE_URL` | No | Use this when targeting a compatible endpoint |
| `SERVER_URL` | Alternative | Remote chat backend URL |
| `SERVER_TOKEN` | Alternative | Auth token for the remote chat backend |
| `EMBEDDING_URL` | Only for RAG | Embedding service endpoint |
| `QDRANT_URL` | Only for RAG | Qdrant instance URL |
| `QDRANT_COLLECTION` | Only for RAG | Collection name, defaults to `magdeburg` |

Notes:

- The dashboard pages can still load from local data even if no LLM is configured.
- Chat and RAG features need an LLM backend.
- RAG also needs an embedding service and a running Qdrant instance.

## Example Questions

You can ask the assistant things like:

- `What's the weather in Magdeburg today?`
- `How many people live in Magdeburg?`
- `Show rent prices by district in Magdeburg for 2024.`
- `How has public transport usage changed in Magdeburg?`
- `Which public transport stops are near Alter Markt in Magdeburg?`
- `Which smart city projects are being funded in Magdeburg according to the documents?`

More demo prompts are available in [DEMO_README.md](./DEMO_README.md).

## Data Sources

This repository mixes several kinds of sources:

- local open-data exports stored in `data/`
- prepared JSON summaries used by the frontend
- live external sources for selected tools such as weather and current web results
- curated RAG documents for Magdeburg strategy, tourism, culture, history, and city information

## RAG Mode

RAG is optional, but supported.

When configured, the app can search a curated Magdeburg knowledge base and answer questions grounded in those sources. The retrieval layer uses:

- embeddings from an external embedding service
- Qdrant for vector search
- curated documents in [`data/rag/`](./data/rag/)

If you only want to run the dashboard and the basic tool-enabled assistant, you do not need to configure RAG.

## Scope and Limitations

- The assistant is intentionally restricted to Magdeburg-related questions.
- If the user asks about another city, the assistant should refuse.
- Some answers depend on live sources and may vary over time.
- RAG answers are only available when the retrieval stack is configured.

## Docker

A `Dockerfile` is included in the repository, but the simplest and most reliable way to run the full project locally is the `uv` workflow shown above.

## Why This Repo Is Useful

This project is a good starting point if you want to build:

- a city dashboard
- a domain-specific AI assistant
- a local-government or civic-tech demo
- a hybrid app that combines structured data, live APIs, and RAG
