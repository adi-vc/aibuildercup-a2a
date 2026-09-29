"""
main.py — Vachan API entry point (FastAPI).

Services:
  POST  /v1/sources             ingest a URL or file → source_id (P0+)
  POST  /v1/sources/upload      file upload variant
  POST  /v1/brain/build         extract + verify → run_id (P1)
  GET   /v1/brain/{source_id}   facts + spans + coverage (P1)
  POST  /v1/gates/{run_id}/ground   gate 1 resume (P1)
  GET   /v1/gates/{run_id}/status   run status poll (P1)
  GET   /v1/manifest/{id}       serve a manifest (fixture in P0, CDN in P5+)
  GET   /healthz                Cloud Run health probe

Run locally:
  uvicorn app.main:app --reload --port 8080
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import sources, manifest, brain, gates

app = FastAPI(
    title="Vachan API",
    version=settings.app_version,
    description=(
        "Backend for Vachan — grounded, interactive, personalized video. "
        "Generation and encoding happen here (build time). "
        "The runtime (frontend) only composites."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
# Allow the Vite dev server and Firebase Hosting to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(sources.router)
app.include_router(manifest.router)
app.include_router(brain.router)
app.include_router(gates.router)


# ── Health probe ──────────────────────────────────────────────────────────────
@app.get("/healthz", tags=["ops"], include_in_schema=False)
async def health() -> dict:
    return {"status": "ok", "version": settings.app_version, "env": settings.env}


# ── Root ──────────────────────────────────────────────────────────────────────
@app.get("/", include_in_schema=False)
async def root() -> dict:
    return {
        "name": "Vachan API",
        "version": settings.app_version,
        "docs": "/docs",
    }