"""
ask.py — POST /v1/ask, the claim guard endpoint (vachan-plan.md §30, §35, §42).

Thin HTTP layer over services/guard.py. It loads the canon fact set the
manifest was built from — manifest → brain_version (the Brain run) → source →
canon facts with verified spans — and falls back to the manifest's own
`integrity.facts` for hand-written fixtures. Gemini is optional: with no key,
or if a call fails, the keyword-rules path answers with the facts' own
published sentences, so a question never errors on stage.

  answered → {type: "answered", answer, facts_cited, span_ids, quotes, question_type, binding?, model_used}
  refused  → {type: "refused", refusal_type, reason, nearest_fact, available_subjects, question, model_used}

Every refusal is logged with its type (services/guard.py). The client appends
questions and refusals to the signed play-log.
"""

from __future__ import annotations

import asyncio

import logging
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.config import settings
from app.routers.bindings import resolve_live
from app.routers.manifest import load_manifest
from app.services import guard
from app.services.brain_store import get_store

log = logging.getLogger(__name__)
router = APIRouter(prefix="/v1", tags=["claim-guard"])


class AskRequest(BaseModel):
    manifest_id: str
    question: str = Field(min_length=1, max_length=500)
    locale: str = "en-IN"
    city: str | None = Field(default=None, max_length=40)
    beat_id: str | None = None
    profile_hash: str = Field(default="", max_length=128)


class Quote(BaseModel):
    fact_id: str
    span_id: str
    quote: str


class AnsweredResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    type: Literal["answered"] = "answered"
    answer: str
    facts_cited: list[str]
    span_ids: list[str]
    quotes: list[Quote]
    question_type: str
    question_type_id: int
    binding: dict[str, Any] | None = None
    model_used: str


class NearestFact(BaseModel):
    fact_id: str
    span_id: str
    text: str
    quote: str


class RefusalResponse(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    type: Literal["refused"] = "refused"
    refusal_type: str
    refusal_type_id: int
    reason: str
    nearest_fact: NearestFact | None
    available_subjects: list[str]
    question: str
    model_used: str


# ── Facts the guard may use ──────────────────────────────────────────────────

def canon_facts_for(manifest: dict) -> dict[str, guard.CanonFact]:
    """Every canon fact with a verified span for the manifest's source (§42.3: the whole set, no retrieval)."""
    store = get_store()
    source_id = manifest.get("source_id")
    if not source_id:
        run = store.get_run(manifest.get("brain_version", "")) or {}
        source_id = run.get("source_id")
    facts: dict[str, guard.CanonFact] = {}
    if source_id:
        spans = {sp["id"]: sp.get("text", "") for sp in store.get_spans(source_id)}
        for f in store.get_facts_by_source(source_id):
            if f.get("origin") == "canon" and f.get("span_id"):
                facts[f["id"]] = guard.CanonFact(
                    id=f["id"], span_id=f["span_id"], text=f.get("text", ""), value=str(f.get("value", "")),
                    unit=f.get("unit", ""), quote=spans.get(f["span_id"], ""), predicate=f.get("predicate", ""))
    if not facts:  # hand-written fixtures carry their published facts in the manifest
        index = manifest.get("integrity", {}).get("fact_index", {})
        for fid, f in manifest.get("integrity", {}).get("facts", {}).items():
            if f.get("origin") == "canon" and fid in index:
                facts[fid] = guard.CanonFact(
                    id=fid, span_id=index[fid], text=f.get("text", ""), value=str(f.get("value", "")),
                    unit=f.get("unit", ""), quote=f.get("quote", ""), predicate=_predicate_from_id(fid))
    return facts


def _predicate_from_id(fact_id: str) -> str:
    return fact_id.removeprefix("f_")


def beat_copy_for(manifest: dict) -> dict[str, dict[str, str]]:
    """Gate-2-approved copy per locale for beats that state exactly one fact."""
    return {b["fact_ids"][0]: b.get("text_slots", {}) for b in manifest.get("beats", [])
            if len(b.get("fact_ids", [])) == 1 and not b.get("bindings")}


def _gemini_call(prompt: str) -> str:
    import google.generativeai as genai

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.guard_model)
    response = model.generate_content(prompt, generation_config={
        "temperature": 0, "response_mime_type": "application/json",
        "response_schema": guard.GUARD_RESPONSE_SCHEMA_SDK,
    })
    return response.text


# ── Endpoint ─────────────────────────────────────────────────────────────────

@router.post("/ask")
async def ask_question(req: AskRequest) -> AnsweredResponse | RefusalResponse:
    manifest = load_manifest(req.manifest_id)
    if manifest is None:
        raise HTTPException(status_code=404, detail=f"Manifest '{req.manifest_id}' not found.")
    facts = canon_facts_for(manifest)
    ctx = guard.GuardContext(
        facts=facts, locale=req.locale, city=req.city, beat_copy=beat_copy_for(manifest),
        competitor_exclusions=manifest.get("policy", {}).get("competitor_exclusions", []),
        resolve_binding=resolve_live,
    )
    model = _gemini_call if settings.gemini_api_key else None
    model_name = settings.guard_model if model else "rules"
    # The guard is synchronous (the model call blocks); keep it off the event loop.
    verdict = await asyncio.to_thread(guard.ask, req.question, ctx, model, model_name)

    subjects = [f.text for f in facts.values() if f.predicate != "offer_price"][:6]
    if verdict.kind == "answered":
        cited = [facts[fid] for fid in verdict.fact_ids if fid in facts]
        return AnsweredResponse(
            answer=verdict.text, facts_cited=[f.id for f in cited], span_ids=[f.span_id for f in cited],
            quotes=[Quote(fact_id=f.id, span_id=f.span_id, quote=f.quote) for f in cited],
            question_type=verdict.question_type, question_type_id=guard.TYPES[verdict.question_type],
            binding=verdict.binding, model_used=verdict.model_used,
        )
    nearest = verdict.nearest
    return RefusalResponse(
        refusal_type=verdict.question_type, refusal_type_id=guard.TYPES[verdict.question_type],
        reason=verdict.text,
        nearest_fact=NearestFact(fact_id=nearest.id, span_id=nearest.span_id, text=nearest.text, quote=nearest.quote)
        if nearest else None,
        available_subjects=subjects, question=req.question, model_used=verdict.model_used,
    )



