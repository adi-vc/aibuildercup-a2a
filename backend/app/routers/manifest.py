"""
manifest.py — GET /v1/manifest/{id}

Serves Gate-2-reviewed manifests from the store, falling back to the
hand-written fixtures. Manifest ids are stable across rebuilds (a pasted embed
must keep working), so responses are `no-cache` with a content-hash ETag:
every play revalidates, and an unchanged manifest costs a 304, not a body.
"""

from __future__ import annotations
import hashlib
import json
from pathlib import Path

from fastapi import APIRouter, Header, HTTPException
from fastapi.responses import JSONResponse, Response

from app.services.brain_store import get_store

router = APIRouter(prefix="/v1/manifest", tags=["manifest"])

# Fixtures live here during P0; real manifests will be in GCS + CDN from P5 onward.
FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures"


def manifest_etag(data: dict) -> str:
    """Strong ETag over the canonical JSON — changes iff the manifest changes."""
    canonical = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return '"' + hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20] + '"'


@router.get("/{manifest_id}")
async def get_manifest(manifest_id: str, if_none_match: str | None = Header(default=None)) -> Response:
    """Return a manifest by id, or 304 when the caller's ETag is current."""
    # P3 persists linted, Gate-2-reviewed plans here. P5 moves this lookup to
    # immutable GCS/CDN storage without changing the runtime contract.
    data = get_store().get_manifest(manifest_id)
    if data is None:
        fixture_path = FIXTURES_DIR / f"{manifest_id}.json"
        if not fixture_path.exists():
            raise HTTPException(status_code=404, detail=f"Manifest '{manifest_id}' not found.")
        data = json.loads(fixture_path.read_text())
    etag = manifest_etag(data)
    headers = {
        "Cache-Control": "no-cache",
        "ETag": etag,
        "Access-Control-Allow-Origin": "*",
        # Let cross-origin players (the embed) read the validator.
        "Access-Control-Expose-Headers": "ETag",
    }
    if if_none_match and etag in [t.strip() for t in if_none_match.split(",")]:
        return Response(status_code=304, headers=headers)
    return JSONResponse(content=data, headers=headers)
