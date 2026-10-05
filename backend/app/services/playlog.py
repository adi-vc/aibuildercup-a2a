"""
playlog.py — signed, chained play records (vachan-plan.md §31, §39.10, §64.10).

A play record says what one viewer was shown: which beats, which claims (each
with its span), which live values and where each came from. The server signs
it and chains it to the previous record for the same manifest, so a record
cannot be altered, dropped or reordered without verification failing.

  canonical(record)  sorted keys, compact separators, UTF-8. Records carry no
                     floats (ages are ints, values are strings), so this is a
                     stable serialisation across languages.
  signature          "hmac-sha256:" + HMAC-SHA256(key, canonical(record \\ signature))
  prev_hash          sha256(canonical(previous signed record)), or GENESIS
  seq                position in the manifest's chain, inside the signed bytes

The key comes from PLAYLOG_HMAC_KEY (Secret Manager → Cloud Run env in
production). Local runs without one get an ephemeral per-process key; any
other environment refuses to sign rather than sign with a guessable key.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.config import settings

log = logging.getLogger(__name__)

GENESIS = "0" * 64
SIGNATURE_PREFIX = "hmac-sha256:"


# ── Record shape (what the client submits) ───────────────────────────────────

class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fact_id: str
    span_id: str


class ShownBinding(BaseModel):
    """One resolved binding exactly as it was on screen (§24.2 receipt column)."""
    model_config = ConfigDict(extra="forbid")
    display: str
    rung: Literal[1, 2, 3, 4]
    value: str | None = None
    unit: str | None = None
    source: dict[str, Any]


class Segment(BaseModel):
    """A stretch of play during which the screen showed exactly this."""
    model_config = ConfigDict(extra="forbid")
    beat_id: str
    locale: str
    city: str
    claims: list[Claim] = Field(default_factory=list, max_length=32)
    bindings: dict[str, ShownBinding] = Field(default_factory=dict)


class PlayRecordIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    manifest_id: str
    manifest_version: str
    profile_hash: str = Field(max_length=128)
    started_at: str
    ended_at: str
    shown: list[Segment] = Field(min_length=1, max_length=500)
    # Filled by P7 (the claim guard); present now so receipts already count them.
    questions: list[str] = Field(default_factory=list, max_length=100)
    refusals: list[dict[str, Any]] = Field(default_factory=list, max_length=100)


# ── Canonical form, hashing, signing ─────────────────────────────────────────

def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def record_hash(record: dict) -> str:
    """The value the *next* record stores as prev_hash (covers the signature too)."""
    return hashlib.sha256(canonical(record)).hexdigest()


_ephemeral_key: bytes | None = None


def _signing_key() -> bytes:
    global _ephemeral_key
    if settings.playlog_hmac_key:
        return settings.playlog_hmac_key.encode("utf-8")
    if settings.env != "local":
        raise RuntimeError("PLAYLOG_HMAC_KEY is not configured; refusing to sign play records.")
    if _ephemeral_key is None:
        _ephemeral_key = secrets.token_bytes(32)
        log.warning("PLAYLOG_HMAC_KEY unset — using an ephemeral local key; signatures will not survive a restart.")
    return _ephemeral_key


def key_id() -> str:
    """Identifies which key signed a record (for rotation) without revealing it."""
    return hashlib.sha256(_signing_key()).hexdigest()[:12]


def sign(record: dict) -> str:
    unsigned = {k: v for k, v in record.items() if k != "signature"}
    return SIGNATURE_PREFIX + hmac.new(_signing_key(), canonical(unsigned), hashlib.sha256).hexdigest()


def verify_signature(record: dict) -> bool:
    claimed = record.get("signature", "")
    return isinstance(claimed, str) and hmac.compare_digest(claimed, sign(record))


def seal(body: PlayRecordIn, seq: int, prev_hash: str | None) -> tuple[dict, str]:
    """Add server fields, sign, and return (record, its chain hash)."""
    record = body.model_dump(mode="json")
    record.update({
        "play_id": f"p_{uuid.uuid4().hex[:12]}",
        "seq": seq,
        "prev_hash": prev_hash or GENESIS,
        "received_at": datetime.now(timezone.utc).isoformat(),
        "key_id": key_id(),
    })
    record["signature"] = sign(record)
    return record, record_hash(record)


# ── Validation against the manifest that was played ──────────────────────────

def validate_against_manifest(body: PlayRecordIn, manifest: dict) -> list[str]:
    """
    Refuse to sign a record that could not have come from this manifest: every
    beat, locale, claim→span and binding provenance must be one the manifest
    allows. Signing is an attestation, so it never covers an impossible screen.
    """
    errors: list[str] = []
    beats = {b["id"]: b for b in manifest.get("beats", [])}
    locales = set(manifest.get("locales", []))
    integrity = manifest.get("integrity", {})
    fact_index: dict[str, str] = integrity.get("fact_index", {})
    published: dict[str, dict] = integrity.get("facts", {})
    resolvers = {b["key"]: b["resolver"] for b in manifest.get("bindings", [])}

    for i, seg in enumerate(body.shown):
        where = f"shown[{i}]"
        beat = beats.get(seg.beat_id)
        if beat is None:
            errors.append(f"{where}: beat '{seg.beat_id}' is not in the manifest")
            continue
        if seg.locale not in locales:
            errors.append(f"{where}: locale '{seg.locale}' is not declared by the manifest")
        for claim in seg.claims:
            if claim.fact_id not in beat.get("fact_ids", []):
                errors.append(f"{where}: beat '{seg.beat_id}' does not cite '{claim.fact_id}'")
            elif fact_index.get(claim.fact_id) != claim.span_id:
                errors.append(f"{where}: '{claim.fact_id}' resolves to span '{fact_index.get(claim.fact_id)}', not '{claim.span_id}'")
        for key, shown in seg.bindings.items():
            if key not in beat.get("bindings", []):
                errors.append(f"{where}: beat '{seg.beat_id}' has no binding '{key}'")
                continue
            kind = shown.source.get("kind")
            if shown.rung in (1, 2):
                expected = "binding" if shown.rung == 1 else "binding_stale"
                if kind != expected or shown.source.get("resolver") != resolvers.get(key) or not shown.value:
                    errors.append(f"{where}: rung {shown.rung} '{key}' must be a {expected} from '{resolvers.get(key)}' with a value")
            elif shown.rung == 3:
                fid = shown.source.get("fact_id")
                if kind != "fact" or fid not in beat.get("fact_ids", []):
                    errors.append(f"{where}: rung 3 '{key}' must cite a fact this beat cites")
                elif shown.source.get("span_id") != fact_index.get(fid):
                    errors.append(f"{where}: rung 3 '{key}' cites the wrong span for '{fid}'")
                elif fid not in published or published[fid].get("value") != shown.value:
                    errors.append(f"{where}: rung 3 '{key}' value differs from the published fact '{fid}'")
            elif kind != "omitted" or shown.value is not None:
                errors.append(f"{where}: rung 4 '{key}' must be omitted and carry no value")
    return errors


# ── Chain verification ───────────────────────────────────────────────────────

def verify_chain(records: list[dict]) -> dict:
    """Verify every signature and link of one manifest's chain, in seq order."""
    failures: list[dict] = []
    prev = GENESIS
    for expected_seq, record in enumerate(sorted(records, key=lambda r: r.get("seq", -1))):
        seq = record.get("seq")
        if seq != expected_seq:
            failures.append({"seq": seq, "play_id": record.get("play_id"), "reason": f"expected seq {expected_seq} (gap or duplicate)"})
        if not verify_signature(record):
            failures.append({"seq": seq, "play_id": record.get("play_id"), "reason": "signature does not verify"})
        if record.get("prev_hash") != prev:
            failures.append({"seq": seq, "play_id": record.get("play_id"), "reason": "prev_hash does not match the previous record"})
        prev = record_hash(record)
    return {"ok": not failures, "count": len(records), "head": prev, "failures": failures}
