# Vachan — Backend (API)

FastAPI service that runs the Vachan build pipeline at build time.
The player (frontend) only ever calls this at play time for:
`/v1/manifest/{id}`, `/ask`, `/bindings/resolve`, `/playlog`.

## Requirements

- **Python 3.11+** (not 3.9 — pre-built `cryptography` wheels require 3.11+ on macOS)
- Docker (for local GCS emulation via `docker compose`)

## Local dev (with docker compose — recommended)

```bash
# From the repo root:
docker compose up          # starts fake-gcs-server + the API with hot-reload

# The API is now at http://localhost:8080
# Swagger UI: http://localhost:8080/docs
```

## Local dev (without Docker)

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

# Copy and fill in environment config
cp .env.example .env
# Set GCS_EMULATOR_HOST=http://localhost:4443 if running fake-gcs separately,
# or leave GCS_BUCKET and GOOGLE_CLOUD_PROJECT pointing at a real GCP project.

uvicorn app.main:app --reload --port 8080
```

## Tests

```bash
cd backend
source .venv/bin/activate
python -m pytest tests/ -v
```

Expected: **6 passed**.

## Key endpoints (P0)

| Method | Path | What |
|--------|------|------|
| `POST` | `/v1/sources` | Ingest a URL → snapshot to GCS → return `source_id` + stub facts |
| `POST` | `/v1/sources/upload` | File upload variant |
| `GET`  | `/v1/manifest/{id}` | Serve a manifest (fixture in P0, CDN in P5+) |
| `GET`  | `/healthz` | Cloud Run health probe |
| `GET`  | `/docs` | Swagger UI |

## Structure

```
backend/
  app/
    main.py           FastAPI app + CORS + routers
    config.py         Settings from env vars
    models/
      brain.py        Pydantic types: Entity, Fact, Span, Source + P0 stub facts
    routers/
      sources.py      POST /v1/sources
      manifest.py     GET /v1/manifest/{id}
    services/
      storage.py      GCS wrapper (emulator-aware)
  fixtures/
    vega_v1.html      Authoritative Vega V1 source document (all 8 facts as verbatim spans)
    p0_single_beat.json  Hand-written single-beat manifest (the P2 linter will validate this)
  tests/
    test_health.py
    test_manifest.py
  Dockerfile          Multi-stage, Python 3.11-slim, non-root user
  requirements.txt
```

## Deployment

See `cloudbuild.yaml` in the repo root. Fill in `YOUR_PROJECT_ID` and `YOUR_REGION` in `cloudrun-service.yaml` before deploying manually.
