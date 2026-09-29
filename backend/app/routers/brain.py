"""
brain.py router — Brain build and query endpoints.

POST /v1/brain/build   { source_id, gcs_path }  → run_id (runs synchronously in P1;
                                                   async Cloud Tasks job in P3+)
GET  /v1/brain/{source_id}                       → BrainResult (facts, spans, coverage)
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.pipeline.brain_builder import run_brain_build, get_brain_result
from app.models.brain import BrainResult, BrainRun
from app.services.brain_store import get_store

router = APIRouter(prefix="/v1/brain", tags=["brain"])


# ── Request / response shapes ─────────────────────────────────────────────────

class BuildRequest(BaseModel):
    source_id: str
    # gcs_path is optional: if omitted the builder tries to look it up from the
    # store (where POST /v1/sources already wrote the source record).
    gcs_path: str = ""


class BuildResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    run_id: str
    source_id: str
    status: str
    coverage: float
    fact_count: int
    canon_count: int
    inferred_count: int
    model_used: str
    offline: bool
    message: str


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/build", response_model=BuildResponse, status_code=202)
async def build_brain(body: BuildRequest) -> BuildResponse:
    """
    Start a brain build for a previously ingested source.

    P1: runs synchronously in the request (no Cloud Tasks yet).
    The run pauses at gate 1 (status=awaiting_gate) and must be resumed via
    POST /v1/gates/{run_id}/ground.

    Returns immediately with the run result including coverage and fact counts.
    """
    store = get_store()

    # Resolve gcs_path from the store if not provided
    gcs_path = body.gcs_path
    if not gcs_path:
        source_doc = store.get_source(body.source_id)
        if source_doc:
            gcs_path = source_doc.get("gcs_path", "")

    try:
        run: BrainRun = run_brain_build(body.source_id, gcs_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return BuildResponse(
        run_id=run.id,
        source_id=run.source_id,
        status=run.status,
        coverage=run.coverage,
        fact_count=run.fact_count,
        canon_count=run.canon_count,
        inferred_count=run.inferred_count,
        model_used=run.model_used,
        offline=run.offline,
        message=(
            f"Brain build complete — {run.fact_count} facts, "
            f"coverage {run.coverage * 100:.0f}%. "
            f"Awaiting gate 1 review at POST /v1/gates/{run.id}/ground."
        ),
    )


@router.get("/{source_id}", response_model=BrainResult)
async def get_brain(source_id: str) -> BrainResult:
    """
    Return the latest brain result for a source: entities, facts, spans, coverage.

    Used by the Studio gate-1 screen to show facts with their source spans.
    Returns 404 if no brain build has been run for this source yet.
    """
    result = get_brain_result(source_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"No brain build found for source '{source_id}'. "
                   "Run POST /v1/brain/build first.",
        )
    return result
