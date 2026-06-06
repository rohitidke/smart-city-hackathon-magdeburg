# MD-Hackathon Dashboard

Small FastAPI dashboard app with a Jinja2 template frontend.

## Project Structure

- `app/main.py` - FastAPI app entrypoint
- `app/templates/dashboard.html` - HTML template
- `pyproject.toml` - Python dependencies
- `Dockerfile` - Docker image definition

## Run Locally With uv

Install dependencies:

```bash
uv sync
```

Create a local env file for secrets:

```bash
OPENAI_API_KEY=your_key_here
OPENAI_BASE_URL=https://eu.api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

Start the development server:

```bash
uv run uvicorn app.main:app --reload
```

Open in browser:

```text
http://127.0.0.1:8000/
```

## Docker

Build the image:

```bash
docker build -t md-dashboard .
```

Run the container:

```bash
docker run --rm -p 8080:8080 md-dashboard
```

Open in browser:

```text
http://127.0.0.1:8080/
```

## GitHub Actions

The workflow can be triggered manually from GitHub Actions:

- Workflow file: `.github/workflows/build.yaml`
- Trigger type: `workflow_dispatch`

## Quick Start

Local development:

```bash
uv sync
uv run uvicorn app.main:app --reload
```

Docker:

```bash
docker build -t md-dashboard .
docker run --rm -p 8080:8080 md-dashboard
```

## Smart Agent Example Queries

- `What's the weather in Magdeburg today?`
  Deutsch: `Wie ist das Wetter heute in Magdeburg?`
  Tool: `wetter_aktuell`
- `What is the current air quality in Magdeburg?`
  Deutsch: `Wie ist die aktuelle Luftqualität in Magdeburg?`
  Tool: `luftqualitaet`
- `How many cafes are there in Magdeburg?`
  Deutsch: `Wie viele Cafés gibt es in Magdeburg?`
  Tool: `cafes`
- `Show rent prices by district in Magdeburg for 2024.`
  Deutsch: `Zeige Mietpreise nach Stadtteil in Magdeburg für 2024.`
  Tool: `miete_preise`
- `How many people live in Magdeburg?`
  Deutsch: `Wie viele Menschen leben in Magdeburg?`
  Tool: `bevoelkerung`
- `What are the latest tax revenues in Magdeburg?`
  Deutsch: `Wie hoch sind die aktuellen Steuereinnahmen in Magdeburg?`
  Tool: `steuer_einnahmen`
- `How has employment in Magdeburg changed over time?`
  Deutsch: `Wie hat sich die Beschäftigung in Magdeburg entwickelt?`
  Tool: `wirtschaft_trends`
- `How many doctors and pharmacies are there in Magdeburg?`
  Deutsch: `Wie viele Ärzte und Apotheken gibt es in Magdeburg?`
  Tool: `gesundheitsversorgung`
- `What events can I attend in Magdeburg today?`
  Deutsch: `Welche Veranstaltungen kann ich heute in Magdeburg besuchen?`
  Tool: `veranstaltungen`
- `How has public transport usage changed in Magdeburg?`
  Deutsch: `Wie hat sich die ÖPNV-Nutzung in Magdeburg entwickelt?`
  Tool: `mobilitaet_trends`
- `Which public transport stops are near Alter Markt in Magdeburg?`
  Deutsch: `Welche ÖPNV-Haltestellen liegen nahe dem Alten Markt in Magdeburg?`
  Tool: `nahverkehr`
- `What is the current Elbe water level in Magdeburg?`
  Deutsch: `Wie ist der aktuelle Elbe-Wasserstand in Magdeburg?`
  Tool: `elbe_pegel`
- `Show climate data for Magdeburg in 2024.`
  Deutsch: `Zeige Klimadaten für Magdeburg im Jahr 2024.`
  Tool: `klima_daten`
- `How has solar energy and LED streetlight conversion developed in Magdeburg?`
  Deutsch: `Wie haben sich Solarenergie und die LED-Umrüstung der Straßenbeleuchtung in Magdeburg entwickelt?`
  Tool: `energie_klima_trends`
- `Give me tree statistics for Magdeburg.`
  Deutsch: `Gib mir Baumstatistiken für Magdeburg.`
  Tool: `baum_statistik`
- `Analyze traffic accidents in Magdeburg in 2023.`
  Deutsch: `Analysiere Verkehrsunfälle in Magdeburg im Jahr 2023.`
  Tool: `unfall_analyse`
- `Which smart city projects are being funded in Magdeburg?`
  Deutsch: `Welche Smart-City-Projekte werden in Magdeburg gefördert?`
  Tool: `rag_suche`

## RAG Example Queries

- `What do the documents say about mobility and public transport in Magdeburg?`
  Deutsch: `Welche Aussagen gibt es in den Dokumenten zu Mobilität und ÖPNV in Magdeburg?`
- `Which smart city projects are being funded in Magdeburg according to the documents?`
  Deutsch: `Welche Smart-City-Projekte werden laut den Dokumenten in Magdeburg gefördert?`
- `Summarize what the indexed sources say about housing in Magdeburg.`
  Deutsch: `Fasse zusammen, was die indexierten Quellen über Wohnen in Magdeburg sagen.`

## Out of scope

- `What is the capital of France?`
  Deutsch: `Was ist die Hauptstadt von Frankreich?`
- `Who will win the football world cup 2026?`
  Deutsch: `Wer wird die Fußball-WM 2026 gewinnen?`
- `Show me rent prices in Berlin.`
  Deutsch: `Zeige mir Mietpreise in Berlin.`
