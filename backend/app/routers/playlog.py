"""
playlog.py — the signed play-log (vachan-plan.md §31, §35, §64.10).

  POST /v1/playlog                       { record }  → the signed, chained record
  GET  /v1/playlog/{play_id}             → one signed record
  POST /v1/playlog/verify                { record }  → does this record's signature verify?
  GET  /v1/playlog/chain/{manifest_id}   → every record of the manifest's chain, verified

POST accepts JSON with any content type: the player sends `text/plain` from
`fetch(..., {keepalive: true})` on page hide, which avoids a CORS preflight a
closing page may not live to complete.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from pydantic import ValidationError

from app.routers.manifest import load_manifest, manifest_etag
from app.services import playlog
from app.services.brain_store import get_store

router = APIRouter(prefix="/v1/playlog", tags=["playlog"])

MAX_BODY_BYTES = 256 * 1024


@router.post("", status_code=201)
async def submit_play(request: Request) -> dict:
    raw = await request.body()
    if len(raw) > MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail="Play record too large.")
    try:
        body = playlog.PlayRecordIn.model_validate(json.loads(raw or b"{}"))
    except (ValueError, ValidationError) as exc:
        raise HTTPException(status_code=422, detail=f"Malformed play record: {exc}") from exc

    manifest = load_manifest(body.manifest_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail=f"Manifest '{body.manifest_id}' not found.")
    if manifest_etag(manifest).strip('"') != body.manifest_version.strip('"'):
        raise HTTPException(status_code=409, detail="Manifest changed since this play started; the record cannot be attested.")
    errors = playlog.validate_against_manifest(body, manifest)
    if errors:
        raise HTTPException(status_code=422, detail={"message": "Record does not match the manifest.", "errors": errors})

    try:
        return get_store().append_play(body.manifest_id, lambda seq, prev: playlog.seal(body, seq, prev))
    except RuntimeError as exc:  # no signing key outside local
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/verify")
async def verify_record(record: dict) -> dict:
    """Recompute the signature over exactly the submitted fields."""
    return {"ok": playlog.verify_signature(record), "play_id": record.get("play_id")}


@router.get("/chain/{manifest_id}")
async def verify_manifest_chain(manifest_id: str) -> dict:
    records = get_store().get_plays_by_manifest(manifest_id)
    return {"manifest_id": manifest_id, **playlog.verify_chain(records)}


@router.get("/{play_id}")
async def get_play(play_id: str) -> dict:
    record = get_store().get_play(play_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"Play '{play_id}' not found.")
    return record
