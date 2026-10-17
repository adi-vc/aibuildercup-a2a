"""P3 planner tests — each §64.5 exit criterion is mechanically asserted."""

import asyncio
import pytest

from app.models.brain import BeatEdit, GateGroundPayload, GatePlanPayload
from app.pipeline.brain_builder import apply_gate_ground, run_brain_build
from app.pipeline.planner import apply_gate_plan, get_plan_manifest, run_plan_build
from app.services.brain_store import get_store, reset_store
from manifest_schema.linter import ManifestLinter


def build_brain(source_id: str, gcs_path: str):
    """run_brain_build is async (non-blocking Gemini calls); run it to completion here."""
    return asyncio.run(run_brain_build(source_id, gcs_path))


SOURCE_ID = "src_test_p3"
GCS_PATH = "gs://vachan-vault-local/sources/src_test_p3/raw.html"


@pytest.fixture(autouse=True)
def fresh_store():
    reset_store()
    yield
    reset_store()


def approved_brain() -> None:
    brain_run = build_brain(SOURCE_ID, GCS_PATH)
    apply_gate_ground(brain_run.id, GateGroundPayload())


def test_planner_produces_seven_to_ten_linted_beats():
    """Criteria 1 and 3: generated plan has 7–10 beats and passes P2 linter."""
    approved_brain()
    run, manifest = run_plan_build(SOURCE_ID)
    assert run.status == "awaiting_gate"
    assert 7 <= len(manifest["beats"]) <= 10
    assert ManifestLinter(manifest).run() == []


def test_every_stating_beat_has_a_canon_fact_and_mood_beats_have_none():
    """Criterion 2: assertion-bearing beats cite verified canon facts only."""
    approved_brain()
    _, manifest = run_plan_build(SOURCE_ID)
    facts = {f["id"]: f for f in get_store().get_facts_by_source(SOURCE_ID)}
    for beat in manifest["beats"]:
        if beat.get("mood"):
            assert beat["fact_ids"] == []
        else:
            assert beat["fact_ids"], beat["id"]
            assert all(facts[fid]["origin"] == "canon" and facts[fid]["span_id"] for fid in beat["fact_ids"])


def test_kids_mode_has_zero_non_sponsor_slots():
    """Criterion 4: safety is enforced by generated data + linter, not UI."""
    approved_brain()
    _, manifest = run_plan_build(SOURCE_ID, kids_mode=True)
    assert manifest["policy"]["kids_mode"] is True
    assert all(slot["kind"] == "sponsor_card" for slot in manifest["slots"])
    assert ManifestLinter(manifest).run() == []


def test_price_binding_and_canon_offer_fallback_are_both_present():
    """Criterion 5: dynamic price has a resolver and published fact fallback."""
    approved_brain()
    _, manifest = run_plan_build(SOURCE_ID)
    assert {binding["key"]: binding["resolver"] for binding in manifest["bindings"]}["price"] == "offer.by_city"
    facts = {f["id"]: f for f in get_store().get_facts_by_source(SOURCE_ID)}
    for fact_id in ("offer_price_mumbai", "offer_price_bengaluru"):
        assert facts[fact_id]["origin"] == "canon"
        assert facts[fact_id]["span_id"]


def test_gate2_edit_persists_and_manifest_stays_linted():
    """Criterion 6: an operator edit resumes Gate 2 and persists."""
    approved_brain()
    run, _ = run_plan_build(SOURCE_ID)
    edited = "Verified range, now with operator-approved copy."
    resumed = apply_gate_plan(run.id, GatePlanPayload(edits=[BeatEdit(
        beat_id="b_range", field="text_slots.en-IN", new_value=edited,
    )]))
    assert resumed.status == "done"
    result = get_plan_manifest(SOURCE_ID)
    assert result is not None
    _, manifest = result
    assert next(b for b in manifest["beats"] if b["id"] == "b_range")["text_slots"]["en-IN"] == edited
    assert ManifestLinter(manifest).run() == []


def test_plan_api_and_gate2_api():
    """Planner is reachable through the build-time API, including Gate 2."""
    from fastapi.testclient import TestClient
    from app.main import app

    approved_brain()
    client = TestClient(app)
    built = client.post("/v1/plan/build", json={"source_id": SOURCE_ID, "kids_mode": False})
    assert built.status_code == 202
    data = built.json()
    assert 7 <= data["beat_count"] <= 10
    reviewed = client.post(f"/v1/gates/{data['run_id']}/plan", json={"edits": []})
    assert reviewed.status_code == 200
    assert reviewed.json()["status"] == "done"
    manifest = client.get(f"/v1/manifest/{data['manifest_id']}")
    assert manifest.status_code == 200
    assert ManifestLinter(manifest.json()).run() == []


def test_manifest_publishes_cited_facts_with_verified_quotes():
    """T5a: integrity.facts carries each cited fact's value and its stored span text."""
    approved_brain()
    _, manifest = run_plan_build(SOURCE_ID)
    published = manifest["integrity"]["facts"]
    assert set(published) == set(manifest["integrity"]["fact_index"])
    spans = {sp["id"]: sp["text"] for sp in get_store().get_spans(SOURCE_ID)}
    for fid, fact in published.items():
        assert fact["origin"] == "canon"
        assert fact["quote"] == spans[manifest["integrity"]["fact_index"][fid]]
    assert published["offer_price_bengaluru"]["value"] == "127400"


def test_manifest_has_hero_edges_with_all_intra_clips_and_a_reachable_branch():
    """T7 / P6: the drag-up spec branch and the click edge, with clip assets and derived plates."""
    approved_brain()
    _, manifest = run_plan_build(SOURCE_ID)
    assert ManifestLinter(manifest).run() == []
    edges = {e["id"]: e for e in manifest["edges"]}
    assert edges["e_flood_spec"]["trigger"] == "drag_up" and edges["e_flood_spec"]["to"] == "b_spec_overlay"
    assert edges["e_range_offer"]["trigger"] == "click"
    beats = {b["id"]: b for b in manifest["beats"]}
    assert beats["b_spec_overlay"]["branch_only"] is True
    assert "e_flood_spec" in beats["b_flood"]["edges"]
    for edge in edges.values():
        assert manifest["vault"][edge["clip"]]["kind"] == "clip"
        target_plate = manifest["vault"][beats[edge["to"]]["vault_refs"][0]]
        assert target_plate["model"] == "derived-last-frame"
    # The spec branch cites real spans for every fact it shows.
    for fid in beats["b_spec_overlay"]["fact_ids"]:
        assert fid in manifest["integrity"]["fact_index"]
