"""
manifest.py — GET /v1/manifest/{id}

P0: serves the hand-written fixture manifest from the local fixtures directory.
P5: this will be replaced by CDN-cached manifests published after the full pipeline runs.
"""

from __future__ import annotations
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/v1/manifest", tags=["manifest"])

# Fixtures live here during P0; real manifests will be in GCS + CDN from P5 onward.
FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"


@router.get("/{manifest_id}")
async def get_manifest(manifest_id: str) -> JSONResponse:
    """
    Return a manifest by id.

    P0: only the fixture manifest 'p0_single_beat' is available.
    """
    fixture_path = FIXTURES_DIR / f"{manifest_id}.json"
    if not fixture_path.exists():
        raise HTTPException(status_code=404, detail=f"Manifest '{manifest_id}' not found.")

    data = json.loads(fixture_path.read_text())
    return JSONResponse(
        content=data,
        headers={
            # Cache-Control will be tightened to immutable once real manifests are published.
            "Cache-Control": "public, max-age=60",
            "Access-Control-Allow-Origin": "*",
        },
    )
