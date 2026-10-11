"""
extractor.py — Fact extraction via Gemini (vachan-plan.md §37.1, §32.1 #1).

Uses google-generativeai with response_schema (structured output) at
temperature=0 so `quote` is copied verbatim from text the model holds in
context — which is what makes the span verifier able to pass.

Design decisions:
- The entire source text goes in one context window (Gemini 2.0 Flash / Pro
  handle 1M tokens; a product page is a few thousand tokens).
- `quote` is the verbatim source substring; the verifier checks it by string
  match and demotes the fact if it fails.
- One fact per statement; volatile predicates (price, stock, offer) are
  flagged so the planner can register them as bindings.
- The extractor never calls the live API when GEMINI_API_KEY is empty and
  ENV != "production" — it returns the fixture stub facts instead.  This
  lets all unit tests run offline.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.config import settings
from app.models.brain import Entity, Fact, STUB_FACTS

log = logging.getLogger(__name__)

# Volatile predicates that the planner must also register as binding keys.
VOLATILE_PREDICATES = frozenset(
    ["price", "offer_price", "stock", "delivery_eta", "offer", "availability"]
)

# ── Extraction prompt ─────────────────────────────────────────────────────────
# Matches vachan-plan.md §37.1 exactly.

SYSTEM_PROMPT = """\
You are a fact extractor for a grounded video system.

Rules (non-negotiable):
1. Extract only what the text STATES explicitly. Never infer.
2. `quote` MUST be copied VERBATIM from the source text, character for character.
   It is checked by string match and the fact is discarded if it fails.
3. One fact per statement. If a sentence states two things, emit two facts.
4. If a value is implied but not stated, omit it.
5. Never infer a comparison, ranking, or superlative.
6. Do not emit relationships between facts.
7. `predicate` must be snake_case, e.g. wading_depth, range_km, zero_to_sixty_s.
8. `text` is one sentence a viewer could read on screen (plain language, not a quote).
9. For entity type use exactly one of: Product, Feature, Place, Character, Concept.
"""

USER_TEMPLATE = """\
Source text:
---
{source_text}
---

Extract all entities and facts from this source. Follow the system rules exactly.
"""

# ── Response schema ───────────────────────────────────────────────────────────
# Passed as response_schema to Gemini's structured-output mode.
# Mirrors the §37.1 JSON schema.

RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["Product", "Feature", "Place", "Character", "Concept"],
                    },
                    "name": {"type": "string"},
                },
                "required": ["type", "name"],
            },
        },
        "facts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "subject":   {"type": "string"},
                    "predicate": {"type": "string"},
                    "value":     {"type": "string"},
                    "unit":      {"type": "string"},
                    "text":      {"type": "string"},
                    "quote":     {"type": "string"},
                },
                "required": ["subject", "predicate", "value", "text", "quote"],
            },
        },
    },
    "required": ["entities", "facts"],
}


# ── Extraction result ─────────────────────────────────────────────────────────

class ExtractionResult:
    def __init__(
        self,
        entities: list[Entity],
        raw_facts: list[dict[str, Any]],  # dicts before verification
        source_id: str,
        model_used: str,
        offline: bool = False,
    ) -> None:
        self.entities = entities
        self.raw_facts = raw_facts          # each has "quote" key for the verifier
        self.source_id = source_id
        self.model_used = model_used
        self.offline = offline              # True when stub data was used


# ── Main function ─────────────────────────────────────────────────────────────

async def extract(source_text: str, source_id: str) -> ExtractionResult:
    """
    Extract entities and raw facts from `source_text`.

    If GEMINI_API_KEY is unset (or ENV=local without a key), returns the
    fixture stub facts so the rest of the pipeline can run offline.
    
    Async to avoid blocking other requests during slow Gemini calls.
    """
    api_key = settings.gemini_api_key
    if not api_key:
        log.warning(
            "GEMINI_API_KEY not set — using P0 stub facts. "
            "Set GEMINI_API_KEY in .env to run real extraction."
        )
        return _stub_result(source_id)

    return await _gemini_extract(source_text, source_id)


async def _gemini_extract(source_text: str, source_id: str) -> ExtractionResult:
    """Call Gemini with structured output and return an ExtractionResult. Async to avoid blocking."""
    import asyncio
    import google.generativeai as genai
    from google.generativeai.types import GenerationConfig

    genai.configure(api_key=settings.gemini_api_key)
    model_name = settings.extraction_model

    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=SYSTEM_PROMPT,
    )

    prompt = USER_TEMPLATE.format(source_text=source_text[:400_000])  # hard cap

    # ── DEBUG: Log the Gemini request ─────────────────────────────────────────
    log.info("=" * 80)
    log.info("🔵 GEMINI EXTRACTION REQUEST")
    log.info("=" * 80)
    log.info(f"Model: {model_name}")
    log.info(f"Source ID: {source_id}")
    log.info(f"Temperature: 0.0")
    log.info(f"Response format: application/json (structured)")
    log.info("-" * 80)
    log.info("SYSTEM PROMPT:")
    log.info(SYSTEM_PROMPT)
    log.info("-" * 80)
    log.info("USER PROMPT (first 1000 chars):")
    log.info(prompt[:1000] + ("..." if len(prompt) > 1000 else ""))
    log.info("-" * 80)
    log.info("RESPONSE SCHEMA:")
    log.info(json.dumps(RESPONSE_SCHEMA, indent=2))
    log.info("=" * 80)

    # Run blocking Gemini call in thread pool
    loop = asyncio.get_event_loop()
    
    def _generate():
        return model.generate_content(
            prompt,
            generation_config=GenerationConfig(
                temperature=0.0,
                response_mime_type="application/json",
                response_schema=RESPONSE_SCHEMA,
            ),
        )
    
    response = await loop.run_in_executor(None, _generate)

    # ── DEBUG: Log the Gemini response ────────────────────────────────────────
    log.info("=" * 80)
    log.info("🟢 GEMINI EXTRACTION RESPONSE")
    log.info("=" * 80)
    log.info(f"Raw response text (first 2000 chars):")
    log.info(response.text[:2000] + ("..." if len(response.text) > 2000 else ""))
    log.info("-" * 80)

    try:
        data = json.loads(response.text)
        log.info(f"Parsed JSON successfully:")
        log.info(f"  - Entities: {len(data.get('entities', []))}")
        log.info(f"  - Facts: {len(data.get('facts', []))}")
        log.info("-" * 80)
        log.info("FULL RESPONSE (formatted):")
        log.info(json.dumps(data, indent=2))
        log.info("=" * 80)
    except (json.JSONDecodeError, AttributeError) as exc:
        log.error("❌ FAILED to parse Gemini response as JSON")
        log.error(f"Response text: {response.text[:500]}")
        log.info("=" * 80)
        raise RuntimeError(
            f"Gemini returned non-JSON response: {response.text[:200]}"
        ) from exc

    entities = [
        Entity(
            id=_entity_id(e["name"]),
            type=e["type"],  # type: ignore[arg-type]
            name=e["name"],
        )
        for e in data.get("entities", [])
    ]

    raw_facts = data.get("facts", [])

    return ExtractionResult(
        entities=entities,
        raw_facts=raw_facts,
        source_id=source_id,
        model_used=model_name,
        offline=False,
    )


def _stub_result(source_id: str) -> ExtractionResult:
    """
    Offline fallback: return the P0 stub facts as raw_facts dicts.
    Each stub fact gets a synthetic `quote` so the verifier has something to
    check against the fixture HTML.
    """
    from app.fixtures import FIXTURE_QUOTES

    raw_facts = []
    for fact in STUB_FACTS:
        raw_facts.append({
            "subject": "Vega V1",   # entity *name*, so _entity_id_from_name matches "Vega V1" → prod_vega_v1
            "predicate": fact.predicate,
            "value": fact.value,
            "unit": fact.unit,
            "text": fact.text,
            "quote": FIXTURE_QUOTES.get(fact.id, fact.text),
        })

    return ExtractionResult(
        entities=[Entity(id="prod_vega_v1", type="Product", name="Vega V1")],
        raw_facts=raw_facts,
        source_id=source_id,
        model_used="stub-offline",
        offline=True,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _entity_id(name: str) -> str:
    """prod_vega_v1 style id from a name."""
    slug = name.lower().replace(" ", "_").replace("-", "_")
    return f"prod_{slug}"
