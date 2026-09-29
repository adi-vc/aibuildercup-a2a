"""
sources.py — POST /v1/sources

P0 implementation:
  • Accepts a URL or raw file upload
  • Fetches the HTML (or reads the file)
  • Snapshots the raw bytes to GCS
  • Returns a source_id and the three hardcoded stub facts

P1 will replace the stub facts with real Gemini extraction + span verification.
"""

from __future__ import annotations
import hashlib
import datetime
import uuid

import httpx
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl

from app.config import settings
from app.models.brain import Source, STUB_FACTS
from app.services import storage as gcs

router = APIRouter(prefix="/v1/sources", tags=["sources"])


# ── Request / response shapes ─────────────────────────────────────────────────

class IngestURLRequest(BaseModel):
    url: str


class IngestResponse(BaseModel):
    source_id: str
    gcs_path: str
    byte_count: int
    checksum: str
    fetched_at: str
    facts_stub: list[dict]      # P0 only — replaced by real facts in P1
    note: str


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_source_id() -> str:
    return f"src_{uuid.uuid4().hex[:12]}"


async def _fetch_url(url: str) -> bytes:
    """Fetch a URL and return its raw bytes."""
    async with httpx.AsyncClient(follow_redirects=True, timeout=30) as client:
        resp = await client.get(url, headers={"User-Agent": "Vachan-Ingest/0.1"})
        if resp.status_code >= 400:
            raise HTTPException(
                status_code=422,
                detail=f"Upstream returned {resp.status_code} for {url}",
            )
        return resp.content


def _upload_and_build_source(raw: bytes, url: str) -> Source:
    """Upload raw bytes to GCS and return a Source record."""
    source_id = _make_source_id()
    checksum = hashlib.sha256(raw).hexdigest()
    now = datetime.datetime.utcnow()
    blob_path = f"sources/{source_id}/raw.html"

    gcs_uri = gcs.upload_bytes(raw, blob_path, content_type="text/html; charset=utf-8")

    return Source(
        id=source_id,
        url=url,
        checksum=checksum,
        fetched_at=now,
        gcs_path=gcs_uri,
        byte_count=len(raw),
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("", response_model=IngestResponse, status_code=201)
async def ingest_url(body: IngestURLRequest) -> IngestResponse:
    """
    Fetch a URL, snapshot the raw HTML to GCS, and return a source_id.

    P0: also returns the hardcoded three-fact stub so the pipeline has something
    to work with before P1 wires real extraction.
    """
    raw = await _fetch_url(body.url)
    source = _upload_and_build_source(raw, body.url)

    # Attach source_id to the stub facts (so later phases can link them back)
    stub_with_source = [
        {**f.model_dump(), "source_id": source.id}
        for f in STUB_FACTS
    ]

    return IngestResponse(
        source_id=source.id,
        gcs_path=source.gcs_path,
        byte_count=source.byte_count,
        checksum=source.checksum,
        fetched_at=source.fetched_at.isoformat() + "Z",
        facts_stub=stub_with_source,
        note="P0 stub facts — real extraction wired in P1.",
    )


@router.post("/upload", response_model=IngestResponse, status_code=201)
async def ingest_file(file: UploadFile = File(...)) -> IngestResponse:
    """
    Upload an HTML or PDF file directly (alternative to URL ingestion).
    Useful for local fixtures without a running web server.
    """
    raw = await file.read()
    url = f"file://{file.filename}"
    source = _upload_and_build_source(raw, url)

    stub_with_source = [
        {**f.model_dump(), "source_id": source.id}
        for f in STUB_FACTS
    ]

    return IngestResponse(
        source_id=source.id,
        gcs_path=source.gcs_path,
        byte_count=source.byte_count,
        checksum=source.checksum,
        fetched_at=source.fetched_at.isoformat() + "Z",
        facts_stub=stub_with_source,
        note="P0 stub facts — real extraction wired in P1.",
    )
