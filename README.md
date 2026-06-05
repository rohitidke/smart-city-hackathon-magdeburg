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
