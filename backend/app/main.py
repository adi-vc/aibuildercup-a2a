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
  POST  /v1/bindings/resolve    play-time binding values, e.g. price by city (P5)
  POST  /v1/playlog             sign + chain a play record; GET …/{id}, …/chain/{manifest} (P7.5)
  GET   /healthz                Cloud Run health probe

Run locally:
  uvicorn app.main:app --reload --port 8080
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import sources, manifest, brain, gates, plans, bindings, playlog, ask

# ── Logging configuration ─────────────────────────────────────────────────────
# Configure root logger to show INFO level logs (includes our Gemini debug logs)
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:\t%(name)s - %(message)s",
)

# Quiet down some noisy libraries
logging.getLogger("google.auth").setLevel(logging.WARNING)
logging.getLogger("google.api_core").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

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

# ── Startup: Auto-load P0 fixture ────────────────────────────────────────────
@app.on_event("startup")
async def load_p0_fixture():
    """Auto-load the P0 fixture and demo manifest on startup so the ask endpoint works immediately."""
    import json
    from pathlib import Path
    from app.services.brain_store import get_store
    from app.models.brain import STUB_FACTS
    
    try:
        store = get_store()
        
        # Load P0 manifest - try multiple possible paths
        possible_paths = [
            Path("fixtures/p0_single_beat.json"),  # from backend/ directory
            Path(__file__).parent.parent / "fixtures" / "p0_single_beat.json",  # relative to app/
            Path("backend/fixtures/p0_single_beat.json"),  # from project root
        ]
        
        manifest = None
        for fixture_path in possible_paths:
            if fixture_path.exists():
                with open(fixture_path) as f:
                    manifest = json.load(f)
                
                # Ensure source_id is set (required for /v1/ask)
                if "source_id" not in manifest:
                    manifest["source_id"] = "src_p0_fixture"
                
                break
        
        if not manifest:
            logging.warning(f"⚠️  P0 fixture not found. Tried: {[str(p) for p in possible_paths]}")
            return
        
        source_id = manifest["source_id"]
        
        # Load facts with the correct source_id
        from app.models.brain import Fact
        for fact in STUB_FACTS:
            # Create a new Fact with updated source_id
            updated_fact = fact.model_copy(update={"source_id": source_id})
            store.save_fact(updated_fact)
        
        # Save P0 manifest
        store.save_manifest(manifest)
        
        logging.info(f"✅ Auto-loaded P0 fixture: manifest_id={manifest['manifest_id']}, source_id={source_id}, {len(STUB_FACTS)} facts")
        
        # Load demo manifest
        demo_paths = [
            Path("fixtures/demo_vega_v1.json"),
            Path(__file__).parent.parent / "fixtures" / "demo_vega_v1.json",
            Path("backend/fixtures/demo_vega_v1.json"),
        ]
        
        demo_manifest = None
        for demo_path in demo_paths:
            if demo_path.exists():
                with open(demo_path) as f:
                    demo_manifest = json.load(f)
                break
        
        if demo_manifest:
            # Save demo manifest
            store.save_manifest(demo_manifest)
            logging.info(f"✅ Auto-loaded demo manifest: manifest_id={demo_manifest['manifest_id']}, beats={len(demo_manifest.get('beats', []))}, vault_assets={len(demo_manifest.get('vault', {}))}")
        
    except Exception as e:
        logging.warning(f"⚠️  Could not auto-load fixtures: {e}")

# ── CORS ─────────────────────────────────────────────────────────────────────
# Allow the Vite dev server and Firebase Hosting to call the API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.effective_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(sources.router)
app.include_router(manifest.router)
app.include_router(brain.router)
app.include_router(gates.router)
app.include_router(plans.router)
app.include_router(bindings.router)
app.include_router(playlog.router)
app.include_router(ask.router)


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
