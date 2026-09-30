"""P3 build-time planning endpoints.  The browser consumes only the manifest."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.pipeline.planner import get_plan_manifest, run_plan_build

router = APIRouter(prefix="/v1/plan", tags=["planner"])


class PlanBuildRequest(BaseModel):
    source_id: str
    kids_mode: bool = False


class PlanBuildResponse(BaseModel):
    run_id: str
    manifest_id: str
    status: str
    beat_count: int
    kids_mode: bool
    message: str


@router.post("/build", response_model=PlanBuildResponse, status_code=202)
async def build_plan(body: PlanBuildRequest) -> PlanBuildResponse:
    try:
        run, _manifest = run_plan_build(body.source_id, body.kids_mode)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return PlanBuildResponse(
        run_id=run.id, manifest_id=run.manifest_id, status=run.status,
        beat_count=run.beat_count, kids_mode=run.kids_mode,
        message=f"Plan built and linted; awaiting Gate 2 review at POST /v1/gates/{run.id}/plan.",
    )


@router.get("/{source_id}")
async def get_plan(source_id: str, kids_mode: bool = False) -> dict:
    result = get_plan_manifest(source_id, kids_mode)
    if not result:
        raise HTTPException(status_code=404, detail=f"No planner manifest for source '{source_id}'.")
    run, manifest = result
    return {"run_id": run.id, "status": run.status, "manifest": manifest}
