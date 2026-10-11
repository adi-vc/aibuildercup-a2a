"""
brain_builder.py — the P1 brain build pipeline.

Steps (vachan-plan.md §38, §40):
  1. Fetch raw source text from GCS
  2. Extract entities + raw facts (Gemini or offline stub)
  3. Verify each fact's quote against the raw source (§39.1 — mechanical)
  4. Assign fact IDs, build Span records, set origin
  5. Write entities / facts / spans / subject→fact_ids index to the store
  6. Write run status; pause at gate 1 ("awaiting_gate")

Gate 1 resume (POST /v1/gates/{run_id}/ground):
  - Apply operator accepts / edits / drops
  - Mark run "done"
"""

from __future__ import annotations

import hashlib
import logging
import re
import unicodedata
from pathlib import Path
from typing import Any

from app.config import settings
from app.models.brain import (
    BrainRun, Entity, Fact, Span, BrainResult, GateGroundPayload
)
from app.pipeline.extractor import extract, ExtractionResult
from app.services.verifier import verify_span, compute_coverage, VerificationResult
from app.services import brain_store, storage as gcs

log = logging.getLogger(__name__)


# ── Helper: read raw source from GCS (or fall back to fixture file) ───────────

def _read_source_text(source_id: str, gcs_path: str) -> str:
    """
    Read the raw HTML for a source.

    Tries GCS first; if that fails (emulator not running, placeholder project)
    falls back to the fixture file in backend/fixtures/.
    """
    try:
        blob_path = gcs_path.split("/", 3)[-1]   # strip gs://bucket/
        raw = gcs.read_bytes(blob_path)
        return raw.decode("utf-8", errors="replace")
    except Exception as exc:
        log.warning("GCS read failed (%s) — loading fixture file instead.", exc)
        fixture = Path(__file__).parent.parent.parent / "fixtures" / "vega_v1.html"
        if fixture.exists():
            return fixture.read_text(encoding="utf-8")
        raise RuntimeError(
            f"Could not load source text for {source_id}: GCS unavailable and "
            "fixture file not found."
        ) from exc


# ── Fact ID generation ────────────────────────────────────────────────────────

def _make_fact_id(subject: str, predicate: str, value: str) -> str:
    """
    Stable, human-readable fact ID.

    For fixture predicates we use the well-known IDs from §17 so downstream
    manifests and tests stay stable.  When predicate alone is ambiguous (e.g.
    `offer_price` appears for both Mumbai and Bengaluru) we include enough of
    the value to disambiguate.
    """
    # Well-known mappings keyed by (subject, predicate, value_fragment).
    # value_fragment is matched as a substring of the lowercased value.
    _KNOWN_WITH_VALUE: list[tuple[tuple[str, str], str, str]] = [
        # (subject, predicate),  value_fragment,  fact_id
        (("prod_vega_v1", "offer_price"),    "129900",   "offer_price_mumbai"),
        (("prod_vega_v1", "offer_price"),    "127400",   "offer_price_bengaluru"),
    ]
    for (subj, pred), val_frag, fact_id in _KNOWN_WITH_VALUE:
        if subject == subj and predicate == pred and val_frag in value.lower().replace(",", ""):
            return fact_id

    # Well-known mappings keyed by (subject, predicate) alone (unambiguous)
    _KNOWN = {
        ("prod_vega_v1", "wading_depth"):        "f_wading_depth",
        ("prod_vega_v1", "range_km"):            "f_range",
        ("prod_vega_v1", "zero_to_sixty_s"):     "f_zero_sixty",
        ("prod_vega_v1", "charge_time_0_80"):    "f_charge_time",
        ("prod_vega_v1", "ground_clearance_mm"): "f_ground_clearance",
        ("prod_vega_v1", "battery_warranty"):    "warranty",
    }
    key = (subject, predicate)
    if key in _KNOWN:
        return _KNOWN[key]

    # Generic fallback: subject__predicate, sanitized
    slug = f"{subject}__{predicate}"
    slug = re.sub(r"[^\w]", "_", slug)[:60]
    return slug


def _make_span_id(source_id: str, start: int) -> str:
    return f"sp_{source_id[-6:]}_{start:06d}"


# ── Main pipeline ─────────────────────────────────────────────────────────────

async def run_brain_build(source_id: str, gcs_path: str) -> BrainRun:
    """
    Run the full extraction + verification pipeline for a source.

    Returns a BrainRun with status="awaiting_gate" (gate 1 open for review).
    The run and all facts/spans are already persisted to the store.
    
    Async to avoid blocking other requests during slow Gemini extraction.
    """
    store = brain_store.get_store()
    run = BrainRun(source_id=source_id, step="extract")
    store.save_run(run)

    try:
        # ── Step 1: read source ───────────────────────────────────────────────
        raw_text = _read_source_text(source_id, gcs_path)
        run.step = "extract"
        store.update_run(run.id, {"step": "extract"})

        # ── Step 2: extract (ASYNC) ───────────────────────────────────────────
        result: ExtractionResult = await extract(raw_text, source_id)
        run.model_used = result.model_used
        run.offline = result.offline

        # ── Step 3: verify + build facts/spans ───────────────────────────────
        run.step = "verify_spans"
        store.update_run(run.id, {"step": "verify_spans", "model_used": result.model_used})

        # Save entities
        for entity in result.entities:
            store.save_entity(entity)
        run.entity_count = len(result.entities)

        verify_results: list[VerificationResult] = []
        facts_written: list[Fact] = []

        for raw in result.raw_facts:
            predicate = raw.get("predicate", "")
            subject_name = raw.get("subject", "")
            # Normalise subject name → entity id
            subject_id = _entity_id_from_name(subject_name, result.entities)
            value = str(raw.get("value", ""))
            unit = raw.get("unit", "")
            text = raw.get("text", "")
            quote = raw.get("quote", "")

            fact_id = _make_fact_id(subject_id, predicate, value)

            # Verify the quote
            vr = verify_span(quote, raw_text)
            verify_results.append(vr)

            origin = "canon" if vr.verified else "inferred"

            # Build span record
            span_id = ""
            if vr.verified and vr.start >= 0:
                span_id = _make_span_id(source_id, vr.start)
                span = Span(
                    id=span_id,
                    source_id=source_id,
                    start=vr.start,
                    end=vr.end,
                    text=vr.matched_text or quote,
                )
                store.save_span(span)

            fact = Fact(
                id=fact_id,
                subject=subject_id,
                predicate=predicate,
                value=value,
                unit=unit,
                text=text,
                origin=origin,  # type: ignore[arg-type]
                source_id=source_id,
                span_id=span_id,
                verify_method=vr.method,
                verify_score=vr.score,
            )
            store.save_fact(fact)
            facts_written.append(fact)

        # ── Step 4: compute coverage and update run ───────────────────────────
        coverage = compute_coverage(verify_results)
        canon_count = sum(1 for f in facts_written if f.origin == "canon")
        inferred_count = sum(1 for f in facts_written if f.origin == "inferred")

        run.coverage = round(coverage, 4)
        run.fact_count = len(facts_written)
        run.canon_count = canon_count
        run.inferred_count = inferred_count
        run.status = "awaiting_gate"
        run.step = "ground_review"

        store.update_run(run.id, {
            "coverage": run.coverage,
            "fact_count": run.fact_count,
            "canon_count": run.canon_count,
            "inferred_count": run.inferred_count,
            "entity_count": run.entity_count,
            "status": "awaiting_gate",
            "step": "ground_review",
            "offline": run.offline,
        })

        log.info(
            "Brain build complete: source=%s run=%s facts=%d coverage=%.1f%%",
            source_id, run.id, run.fact_count, coverage * 100,
        )

    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)
        store.update_run(run.id, {"status": "failed", "error": str(exc)})
        log.exception("Brain build failed for source=%s", source_id)
        raise

    return run


# ── Gate 1 resume ─────────────────────────────────────────────────────────────

def apply_gate_ground(run_id: str, payload: GateGroundPayload) -> BrainRun:
    """
    Apply operator edits from gate 1 and mark the run done.

    Accepted facts are kept as-is.
    Edited facts have their specified field updated.
    Dropped facts are deleted.
    Any fact not mentioned in accepts/edits/drops is kept (implicit accept).
    """
    store = brain_store.get_store()

    run_dict = store.get_run(run_id)
    if not run_dict:
        raise ValueError(f"Run '{run_id}' not found.")

    run = BrainRun(**run_dict)

    if run.status not in ("awaiting_gate", "done"):
        raise ValueError(
            f"Run '{run_id}' is in status '{run.status}' — cannot apply gate edits."
        )

    # Apply edits
    for edit in payload.edits:
        store.update_fact(edit.fact_id, {edit.field: edit.new_value})
        log.info("Gate 1 edit: fact=%s field=%s → %r", edit.fact_id, edit.field, edit.new_value)

    # Apply drops
    for fact_id in payload.drops:
        store.delete_fact(fact_id)
        log.info("Gate 1 drop: fact=%s", fact_id)

    # Mark run done
    run.status = "done"
    run.step = "ground_review_complete"
    store.update_run(run_id, {"status": "done", "step": "ground_review_complete"})

    return run


# ── Query helpers ──────────────────────────────────────────────────────────────

def get_brain_result(source_id: str) -> BrainResult | None:
    """
    Return the latest brain result for a source_id, or None if not found.
    """
    store = brain_store.get_store()

    runs = store.get_runs_by_source(source_id)
    if not runs:
        return None

    # Pick the most recent run (latest created_at)
    latest = max(runs, key=lambda r: r.get("created_at", ""))
    run = BrainRun(**latest)

    facts_raw = store.get_facts_by_source(source_id)
    spans_raw = store.get_spans(source_id)
    entities_raw = store.get_entities()

    facts = [Fact(**f) for f in facts_raw]
    spans = [Span(**s) for s in spans_raw]
    entities = [Entity(**e) for e in entities_raw]

    return BrainResult(
        source_id=source_id,
        run_id=run.id,
        status=run.status,
        coverage=run.coverage,
        entity_count=run.entity_count,
        fact_count=run.fact_count,
        canon_count=run.canon_count,
        inferred_count=run.inferred_count,
        model_used=run.model_used,
        offline=run.offline,
        entities=entities,
        facts=facts,
        spans=spans,
    )


# ── Internals ─────────────────────────────────────────────────────────────────

def _entity_id_from_name(name: str, entities: list[Entity]) -> str:
    """
    Map a subject name returned by the model to an entity id.
    Tries an exact-name match first; falls back to slug generation.
    The slug does NOT add a `prod_` prefix here — that was already applied
    by the extractor's `_entity_id()` function when the Entity was created.
    """
    for e in entities:
        if e.name.lower() == name.lower():
            return e.id
    # slug fallback — match the extractor's _entity_id() logic exactly
    slug = name.lower().replace(" ", "_").replace("-", "_")
    slug = re.sub(r"[^\w]", "_", slug)
    return f"prod_{slug}" if slug else "prod_unknown"
