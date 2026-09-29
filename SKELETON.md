# P0 Walking Skeleton — Developer Guide

This document covers the P0 skeleton specifically: what was built, how to run it, and what comes next. The public-facing pitch lives in `README.md`; the full plan lives in `vachan-plan.md`.

---

## What P0 proves

The three exit criteria from `vachan-plan.md §64.2`:

1. `POST /v1/sources` against the Vega V1 fixture returns a `source_id` and the raw HTML is readable from GCS.
2. The one-beat manifest (`p0_single_beat`) renders in a browser with a text layer on top, from the deployed URL.
3. A teammate on another machine can open it without a VPN or a local build.

Nothing here is meant to look good. A dark SVG behind white text is success.

---

## Repo layout after P0

```
aibuildercup-a2a/
├── backend/                 FastAPI API + build pipeline (Python 3.11+)
│   ├── app/
│   │   ├── main.py          Entry point, CORS, routers
│   │   ├── config.py        Settings from env vars
│   │   ├── models/brain.py  Entity / Fact / Span types + P0 stub facts
│   │   ├── routers/
│   │   │   ├── sources.py   POST /v1/sources
│   │   │   └── manifest.py  GET /v1/manifest/{id}
│   │   └── services/
│   │       └── storage.py   GCS wrapper (emulator-aware)
│   ├── fixtures/
│   │   ├── vega_v1.html     Authoritative Vega V1 source (all 8 facts, verbatim spans)
│   │   └── p0_single_beat.json  Hand-written single-beat manifest
│   ├── tests/               6 passing tests
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/                React 19 + Vite 8 + TypeScript player
│   ├── src/
│   │   ├── types/manifest.ts   Manifest schema types (§28)
│   │   ├── api/client.ts       fetchManifest(), ingestUrl()
│   │   ├── hooks/useManifest.ts
│   │   └── components/
│   │       └── BeatPlayer.tsx  Plate + text layer + locale select + fact badges
│   ├── public/assets/          SVG placeholder plate
│   ├── firebase.json
│   └── vite.config.ts          Dev proxy → localhost:8080
│
├── docker-compose.yml       Local stack: fake-gcs-server + API with hot-reload
├── cloudbuild.yaml          CI/CD: test → build → Cloud Run → Firebase Hosting
├── cloudrun-service.yaml    Declarative Cloud Run spec
├── models.yaml              Pinned model versions (no model calls yet in P0)
├── vachan-plan.md           The full plan
├── PLAN_TRACKER.md          Task log (T1 = this work)
└── AGENTS.md                Contributor brief
```

---

## Running locally

### Option A — Docker Compose (recommended, no GCP needed)

```bash
# From the repo root
docker compose up

# Backend: http://localhost:8080
# Swagger:  http://localhost:8080/docs

# In a second terminal:
cd frontend && npm install && npm run dev
# Player:  http://localhost:5173
```

### Option B — Without Docker

**Backend:**
```bash
cd backend
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
# Edit .env: set your GCP project + bucket, or set GCS_EMULATOR_HOST for local emulator
uvicorn app.main:app --reload --port 8080
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

### Verify the skeleton works

```bash
# 1. Ingest the fixture (the /upload endpoint takes a file directly)
curl -X POST http://localhost:8080/v1/sources/upload \
  -F "file=@backend/fixtures/vega_v1.html" | jq .

# Expected: { "source_id": "src_...", "facts_stub": [...3 facts...], ... }

# 2. Fetch the manifest
curl http://localhost:8080/v1/manifest/p0_single_beat | jq .manifest_id

# Expected: "p0_single_beat"

# 3. Open the player
open http://localhost:5173
# Expected: dark scooter-scene SVG with "30 cm of water. Still going." overlaid
# Switch the locale dropdown to hi-IN → text changes to Hindi → text is a layer ✓
```

---

## Running tests

```bash
cd backend
source .venv/bin/activate
python -m pytest tests/ -v
# 6 passed
```

---

## Deploying

**Prerequisites (one-time):**
```bash
gcloud services enable run.googleapis.com artifactregistry.googleapis.com \
  cloudbuild.googleapis.com firebasehosting.googleapis.com

gcloud artifacts repositories create vachan \
  --repository-format=docker --location=asia-south1

# Create the GCS vault bucket
gsutil mb -l asia-south1 gs://vachan-vault
```

**Fill in placeholders:**
- `frontend/.firebaserc` → replace `YOUR_FIREBASE_PROJECT_ID`
- `cloudrun-service.yaml` → replace `YOUR_PROJECT_ID`, `YOUR_REGION`, `YOUR_REGION-docker.pkg.dev/...`
- `cloudbuild.yaml` → set `_PROJECT_ID` and `_REGION` substitutions in Cloud Build trigger config

**Manual deploy (for the first time):**
```bash
# Backend
cd backend
gcloud builds submit --config=../cloudbuild.yaml

# Frontend (after backend URL is known)
cd frontend
cp .env.example .env.local
# Set VITE_API_BASE_URL=https://your-api-url.run.app
npm run build
npx firebase deploy --only hosting
```

**Ongoing:** push to `main` → Cloud Build trigger runs `cloudbuild.yaml` end-to-end.

---

## What is NOT in P0 (deliberately)

- No real fact extraction (P1)
- No manifest schema linter (P2)
- No beat planner (P3)
- No generated images, TTS, or transition clips (P4)
- No locale/city swap, no embed (P5)
- No gesture scrubbing (P6)
- No claim guard (P7)

The three stub facts in `backend/app/models/brain.py` stand in for everything P1 will produce.
The SVG placeholder in `frontend/public/assets/` stands in for the Vault images P4 will generate.

---

## Known shortcut (logged per AGENTS.md §6)

**Python version:** `google-cloud-storage` pulls in `cryptography`, which requires Python 3.11+ for pre-built wheels on macOS (no OpenSSL dev headers). The backend venv must be created with `python3.11`. The Dockerfile uses `python:3.11-slim` to match. This is not a debt — 3.11 is the right choice — but it is worth noting for teammates on machines where `python3` defaults to 3.9.
