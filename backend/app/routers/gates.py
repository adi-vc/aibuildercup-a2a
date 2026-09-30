"""
gates.py router — Human approval gates (vachan-plan.md §40, §29).

POST /v1/gates/{run_id}/ground   gate 1: accept / edit / drop facts, resume run
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.brain import GateGroundPayload, GatePlanPayload
from app.pipeline.brain_builder import apply_gate_ground
from app.pipeline.planner import apply_gate_plan
from app.services.brain_store import get_store

router = APIRouter(prefix="/v1/gates", tags=["gates"])


# ── Response ──────────────────────────────────────────────────────────────────

class GateResponse(BaseModel):
    run_id: str
    status: str
    message: str


# ── Gate 1: ground review ─────────────────────────────────────────────────────

@router.post("/{run_id}/ground", response_model=GateResponse)
async def gate_ground(run_id: str, payload: GateGroundPayload) -> GateResponse:
    """
    Resume a brain build after gate 1 (fact review).

    The operator:
      - `accepts` a list of fact_ids to keep unchanged (implicit for all others)
      - `edits`   a list of {fact_id, field, new_value} corrections
      - `drops`   a list of fact_ids to remove entirely

    Any fact not listed in accepts/edits/drops is kept as-is.

    After this call:
      - Edited facts are updated in the store
      - Dropped facts are deleted
      - The run moves to status="done"

    Edits persist across restarts (stored in Firestore / in-memory store).
    """
    store = get_store()

    run_dict = store.get_run(run_id)
    if not run_dict:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")

    status = run_dict.get("status", "")
    if status == "running":
        raise HTTPException(
            status_code=409,
            detail=f"Run '{run_id}' is still running — wait for status=awaiting_gate.",
        )
    if status == "failed":
        raise HTTPException(
            status_code=422,
            detail=f"Run '{run_id}' failed — start a new build.",
        )

    try:
        run = apply_gate_ground(run_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    n_edits = len(payload.edits)
    n_drops = len(payload.drops)
    return GateResponse(
        run_id=run.id,
        status=run.status,
        message=(
            f"Gate 1 accepted. Applied {n_edits} edit(s) and {n_drops} drop(s). "
            "Run is now done — proceed to POST /v1/plan/build."
        ),
    )


# ── Gate 2: beat plan review ──────────────────────────────────────────────────

@router.post("/{run_id}/plan", response_model=GateResponse)
async def gate_plan(run_id: str, payload: GatePlanPayload) -> GateResponse:
    """Apply Gate 2 beat-plan edits, re-lint the manifest, and publish it."""
    try:
        run = apply_gate_plan(run_id, payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return GateResponse(
        run_id=run.id,
        status=run.status,
        message=(f"Gate 2 accepted. Applied {len(payload.edits)} edit(s); "
                 "manifest remains lint-clean and is ready for P4 Vault generation."),
    )


# ── Run status (useful for polling) ──────────────────────────────────────────

@router.get("/{run_id}/status", response_model=GateResponse)
async def run_status(run_id: str) -> GateResponse:
    """Poll the current status of a pipeline run."""
    store = get_store()
    run_dict = store.get_run(run_id)
    if not run_dict:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found.")
    return GateResponse(
        run_id=run_id,
        status=run_dict.get("status", "unknown"),
        message=f"Step: {run_dict.get('step', '—')}",
    )
