"""P3 planner: approved facts -> a linted, Vault-ready manifest.

The planner is deliberately build-time only.  Its deterministic ads templates
are the safe fallback for the Gemini structured-output planner: templates make
the beat/fact relationship inspectable, while the P2 linter remains the final
authority before Gate 2 can open.  P4 replaces the planned placeholder vault
assets with generated assets; the manifest contract does not change.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import logging
from typing import Any

from app.config import settings
from app.models.brain import BrainRun, Fact, GatePlanPayload, PlanRun
from app.services import brain_store
from app.pipeline.placeholder_clips import load_registry
from manifest_schema.linter import ManifestLinter


LOCALES = ["en-IN", "hi-IN"]
# Raster placeholder: transition clips are built from these exact pixels (§39.3).
PLACEHOLDER_URI = "/assets/placeholder_flood_street.png"
# Placeholders are content-addressed stand-ins too (§66.2 rule 3): P4 swaps in
# real plates and depth maps without any runtime change.
PLACEHOLDER_DEPTH_URI = "/assets/placeholder_flood_street_depth.svg"
log = logging.getLogger(__name__)

# Gemini is allowed to improve copy only.  The adapter owns IDs, fact
# assignment, bindings and all integrity indexes, so a model can never loosen
# the grounding contract or invent a structural relationship.
PLANNER_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {"beats": {"type": "array", "items": {"type": "object", "properties": {
        "id": {"type": "string"}, "fact_ids": {"type": "array", "items": {"type": "string"}},
        "text_slots": {"type": "object", "properties": {"en-IN": {"type": "string"}, "hi-IN": {"type": "string"}},
                         "required": ["en-IN", "hi-IN"]},
    }, "required": ["id", "fact_ids", "text_slots"]}}},
    "required": ["beats"],
}


def _fact_map(facts: list[Fact]) -> dict[str, Fact]:
    return {fact.id: fact for fact in facts if fact.origin == "canon" and fact.span_id}


def _verified_quote(fact: Fact, span_text: dict[str, str]) -> str:
    """A canon fact's on-screen quote must be its stored span, never a paraphrase."""
    quote = span_text.get(fact.span_id, "")
    if not quote:
        raise ValueError(f"Canon fact '{fact.id}' has no stored span '{fact.span_id}' to quote.")
    return quote


def _text_slots(en: str, hi: str) -> dict[str, str]:
    return {"en-IN": en, "hi-IN": hi}


def _beat(
    beat_id: str, fact_ids: list[str], text: dict[str, str], *, bindings: list[str] | None = None,
    mood: bool = False, branch_only: bool = False,
) -> dict[str, Any]:
    """One hold beat with a P4-replaceable planned plate reference."""
    return {
        "id": beat_id,
        "kind": "hold",
        "mood": mood,
        **({"branch_only": True} if branch_only else {}),
        "fact_ids": fact_ids,
        "vault_refs": [f"plate_{beat_id[2:]}"],
        "text_slots": text,
        "audio_slots": {},
        "bindings": bindings or [],
        "hinge": {"in": "wide_neutral", "out": "wide_neutral"},
        "edges": [],
    }


# The two §18 hero edges with placeholder clips (P6). Veo replaces only the clip
# bytes; ids, triggers and the derived-plate rule stay.
EDGE_SPECS = [
    {"id": "e_flood_spec", "from": "b_flood", "to": "b_spec_overlay", "clip_name": "clip_flood_to_spec",
     "trigger": "drag_up", "reversible": True, "label": "Show me the spec sheet"},
    {"id": "e_range_offer", "from": "b_range", "to": "b_offer", "clip_name": "clip_range_to_offer",
     "trigger": "click", "reversible": False, "label": "See the price in your city"},
]


def _transition_edges(beats: list[dict[str, Any]]) -> tuple[list[dict], dict[str, dict], dict[str, dict]]:
    """
    Add the hero edges whose placeholder clips exist: the edge, its clip asset,
    and the target plate derived from the clip's last frame. The spec-sheet
    branch beat is added only alongside its edge, so it is never unreachable.
    """
    clips = load_registry().get("clips", {})
    by_id = {b["id"]: b for b in beats}
    edges: list[dict] = []
    clip_assets: dict[str, dict] = {}
    derived: dict[str, dict] = {}
    for spec in EDGE_SPECS:
        clip = clips.get(spec["clip_name"])
        if not clip:
            continue
        if spec["to"] == "b_spec_overlay" and "b_spec_overlay" not in by_id:
            branch = _beat("b_spec_overlay", ["f_wading_depth", "f_ground_clearance", "f_charge_time"],
                           _text_slots("From the spec sheet.", "स्पेक शीट से।"), branch_only=True)
            beats.append(branch)
            by_id[branch["id"]] = branch
        edges.append({
            "id": spec["id"], "from": spec["from"], "to": spec["to"], "clip": clip["asset_id"],
            "trigger": spec["trigger"], "reversible": spec["reversible"],
            "duration_s": clip["duration_s"], "label": spec["label"],
        })
        by_id[spec["from"]]["edges"].append(spec["id"])
        clip_assets[clip["asset_id"]] = {
            "kind": "clip", "uri": clip["uri"], "poster_uri": clip["from_plate_uri"], "depth_uri": "",
            "fact_ids": [], "model": "placeholder-ffmpeg", "seed": 0, "bible_version": "pending-p4",
        }
        target_plate = by_id[spec["to"]]["vault_refs"][0]
        derived[target_plate] = {
            "uri": clip["derived_plate"]["uri"], "poster_uri": clip["derived_plate"]["uri"], "depth_uri": "",
            "model": "derived-last-frame",
        }
    return edges, clip_assets, derived


def _manifest_from_facts(
    source_id: str, brain_run: BrainRun, facts: list[Fact], kids_mode: bool,
    span_text: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Create the Vega ads adapter's eight-beat plan from verified facts only."""
    by_id = _fact_map(facts)
    required = {
        "f_wading_depth", "f_range", "f_zero_sixty", "f_charge_time",
        "f_ground_clearance", "offer_price_mumbai", "offer_price_bengaluru", "warranty",
    }
    missing = sorted(required - by_id.keys())
    if missing:
        raise ValueError("Planner requires approved canon facts with verified spans: " + ", ".join(missing))

    beats = [
        _beat("b_hook", [], _text_slots("Built for the road ahead.", "आगे की राह के लिए बनी।"), mood=True),
        _beat("b_flood", ["f_wading_depth"], _text_slots("30 cm of water. Still going.", "30 सेमी पानी। फिर भी चलती रही।")),
        _beat("b_range", ["f_range"], _text_slots("128 km on a charge.", "एक चार्ज में 128 किमी।")),
        _beat("b_performance", ["f_zero_sixty"], _text_slots("0 to 60 in 8.2 seconds.", "8.2 सेकंड में 0 से 60।")),
        _beat("b_charge", ["f_charge_time"], _text_slots("0 to 80% in 4 hours 30 minutes.", "4 घंटे 30 मिनट में 0 से 80%।")),
        _beat("b_clearance", ["f_ground_clearance"], _text_slots("165 mm of ground clearance.", "165 मिमी ग्राउंड क्लियरेंस।")),
        _beat("b_offer", ["offer_price_mumbai", "offer_price_bengaluru"], _text_slots("On-road in your city:", "आपके शहर में:"), bindings=["price"]),
        _beat("b_warranty", ["warranty"], _text_slots("3 years or 30,000 km battery warranty.", "3 साल या 30,000 किमी बैटरी वारंटी।")),
    ]
    edges, clip_assets, derived_plates = _transition_edges(beats)
    cited_fact_ids = sorted({fid for beat in beats for fid in beat["fact_ids"]})
    vault = {
        ref: {
            "kind": "plate", "uri": PLACEHOLDER_URI, "poster_uri": PLACEHOLDER_URI,
            "depth_uri": PLACEHOLDER_DEPTH_URI, "fact_ids": beat["fact_ids"], "model": "planned-p3",
            "seed": 0, "bible_version": "pending-p4",
            # A plate derived from a clip's last frame replaces the shared placeholder (§39.3).
            **derived_plates.get(ref, {}),
        }
        for beat in beats for ref in beat["vault_refs"]
    }
    vault.update(clip_assets)
    beat_index = {fid: [b["id"] for b in beats if fid in b["fact_ids"]] for fid in cited_fact_ids}
    asset_index = {
        fid: [ref for b in beats if fid in b["fact_ids"] for ref in b["vault_refs"]]
        for fid in cited_fact_ids
    }
    slots = [] if kids_mode else [{
        "id": "slot_offer", "beat_id": "b_offer", "kind": "shoppable",
        "policy": {"kids_mode": False, "categories_allowed": ["auto"], "competitor_exclusions": ["brand_x"]},
    }]
    suffix = "kids" if kids_mode else "standard"
    return {
        "manifest_id": f"m_{source_id}_{suffix}", "schema_version": "1.0",
        "brain_version": brain_run.id, "bitgraph_version": f"bg_{brain_run.id[-8:]}",
        "locales": LOCALES, "beats": beats, "edges": edges, "slots": slots,
        "bindings": [{"key": "price", "resolver": "offer.by_city", "ttl_s": 300}],
        "accessibility": {"captions": True, "audio_description": True},
        "policy": {"kids_mode": kids_mode, "competitor_exclusions": ["brand_x"]},
        "vault": vault,
        "integrity": {
            "fact_index": {fid: by_id[fid].span_id for fid in cited_fact_ids},
            # Published values + verified quotes for the runtime's §24.2 rung 3
            # and the inspector; the quote is the stored span, never model text.
            "facts": {
                fid: {
                    "value": by_id[fid].value, "unit": by_id[fid].unit, "text": by_id[fid].text,
                    "quote": _verified_quote(by_id[fid], span_text or {}),
                    "origin": "canon",
                }
                for fid in cited_fact_ids
            },
            "beat_index": beat_index, "asset_index": asset_index,
            "coverage": 1.0, "linted_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def _apply_gemini_copy(manifest: dict[str, Any], facts: list[Fact]) -> str:
    """Optionally replace adapter copy with structured Gemini output.

    Offline and test runs intentionally retain the deterministic template. If
    Gemini responds with a malformed beat/fact mapping, the whole response is
    rejected rather than partially trusted; the linted template remains the
    safe build fallback.
    """
    if not settings.gemini_api_key:
        return "ads-template-v1"
    try:
        import google.generativeai as genai
        genai.configure(api_key=settings.gemini_api_key)
        canon = [{"id": f.id, "text": f.text, "value": f.value, "unit": f.unit} for f in facts if f.origin == "canon"]
        expected = [{"id": b["id"], "fact_ids": b["fact_ids"], "mood": b.get("mood", False)} for b in manifest["beats"]]
        prompt = (
            "You are Vachan's ads planner. Write concise, source-faithful English and Hindi copy for the supplied "
            "beat plan. Return exactly the supplied beat ids and fact_ids. Do not add claims, numbers, comparisons, "
            "or calls to action beyond the facts. A mood beat has no facts and must remain atmospheric.\n"
            f"FACTS={json.dumps(canon, ensure_ascii=False)}\nBEATS={json.dumps(expected)}"
        )
        model = genai.GenerativeModel(settings.planning_model)
        response = model.generate_content(prompt, generation_config={
            "temperature": 0, "response_mime_type": "application/json", "response_schema": PLANNER_RESPONSE_SCHEMA,
        })
        proposed = json.loads(response.text)
        replacement = {beat["id"]: beat for beat in proposed["beats"]}
        if set(replacement) != {b["id"] for b in manifest["beats"]}:
            raise ValueError("response beat ids differ from ads adapter")
        for beat in manifest["beats"]:
            candidate = replacement[beat["id"]]
            if candidate["fact_ids"] != beat["fact_ids"]:
                raise ValueError(f"response changed fact assignment for {beat['id']}")
            slots = candidate["text_slots"]
            if not all(isinstance(slots.get(locale), str) and slots[locale].strip() for locale in LOCALES):
                raise ValueError(f"response omitted a locale for {beat['id']}")
            beat["text_slots"] = {locale: slots[locale].strip() for locale in LOCALES}
        return settings.planning_model
    except Exception as exc:
        log.warning("Gemini planner output rejected; retaining deterministic ads template: %s", exc)
        return "ads-template-v1-fallback"


def _latest_approved_brain_run(source_id: str) -> BrainRun:
    store = brain_store.get_store()
    runs = store.get_runs_by_source(source_id)
    if not runs:
        raise ValueError(f"No Brain run exists for source '{source_id}'. Build and approve it first.")
    run = BrainRun(**max(runs, key=lambda r: r.get("created_at", "")))
    if run.status != "done":
        raise ValueError(f"Brain run '{run.id}' is '{run.status}'; Gate 1 must be completed before planning.")
    return run


def run_plan_build(source_id: str, kids_mode: bool = False) -> tuple[PlanRun, dict[str, Any]]:
    """Build, lint, persist, then pause a P3 manifest at Gate 2."""
    store = brain_store.get_store()
    brain_run = _latest_approved_brain_run(source_id)
    run = PlanRun(source_id=source_id, brain_run_id=brain_run.id, kids_mode=kids_mode)
    store.save_plan_run(run)
    try:
        facts = [Fact(**raw) for raw in store.get_facts_by_source(source_id)]
        span_text = {sp["id"]: sp["text"] for sp in store.get_spans(source_id)}
        manifest = _manifest_from_facts(source_id, brain_run, facts, kids_mode, span_text)
        run.model_used = _apply_gemini_copy(manifest, facts)
        run.offline = not bool(settings.gemini_api_key)
        violations = ManifestLinter(manifest).run()
        if violations:
            details = "; ".join(f"{v.code}: {v.message}" for v in violations)
            raise ValueError(f"Planner produced an invalid manifest: {details}")
        store.save_manifest(manifest)
        run.manifest_id = manifest["manifest_id"]
        run.beat_count = len(manifest["beats"])
        run.status = "awaiting_gate"
        run.step = "plan_review"
        store.update_plan_run(run.id, run.model_dump(mode="json"))
        return run, manifest
    except Exception as exc:
        run.status = "failed"
        run.error = str(exc)
        store.update_plan_run(run.id, {"status": "failed", "error": str(exc)})
        raise


def _set_nested(target: dict[str, Any], dotted_path: str, value: Any) -> None:
    keys = dotted_path.split(".")
    current = target
    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            raise ValueError(f"Unsupported beat edit path '{dotted_path}'.")
        current = current[key]
    if keys[-1] not in current:
        raise ValueError(f"Unsupported beat edit path '{dotted_path}'.")
    current[keys[-1]] = value


def apply_gate_plan(run_id: str, payload: GatePlanPayload) -> PlanRun:
    """Apply constrained operator changes, re-lint, and publish Gate 2's plan."""
    store = brain_store.get_store()
    raw_run = store.get_plan_run(run_id)
    if not raw_run:
        raise ValueError(f"Planner run '{run_id}' not found.")
    run = PlanRun(**raw_run)
    if run.status not in ("awaiting_gate", "done"):
        raise ValueError(f"Planner run '{run_id}' is '{run.status}' and cannot be edited.")
    manifest = store.get_manifest(run.manifest_id)
    if not manifest:
        raise ValueError(f"Manifest '{run.manifest_id}' not found.")
    manifest = deepcopy(manifest)
    beats = {beat["id"]: beat for beat in manifest["beats"]}
    for edit in payload.edits:
        beat = beats.get(edit.beat_id)
        if not beat:
            raise ValueError(f"Beat '{edit.beat_id}' not found.")
        _set_nested(beat, edit.field, edit.new_value)
    violations = ManifestLinter(manifest).run()
    if violations:
        details = "; ".join(f"{v.code}: {v.message}" for v in violations)
        raise ValueError(f"Gate 2 edits would invalidate manifest: {details}")
    manifest["integrity"]["linted_at"] = datetime.now(timezone.utc).isoformat()
    store.save_manifest(manifest)
    run.status = "done"
    run.step = "plan_review_complete"
    store.update_plan_run(run.id, {"status": run.status, "step": run.step})
    return run


def get_plan_manifest(source_id: str, kids_mode: bool = False) -> tuple[PlanRun, dict[str, Any]] | None:
    store = brain_store.get_store()
    runs = [r for r in store.get_plan_runs_by_source(source_id) if r.get("kids_mode") == kids_mode]
    if not runs:
        return None
    run = PlanRun(**max(runs, key=lambda r: r.get("created_at", "")))
    manifest = store.get_manifest(run.manifest_id)
    return (run, manifest) if manifest else None
