"""
test_linter.py — one test per linter invariant (vachan-plan.md §64.4 exit criterion 1).

Rule: each test mutates a single field of an otherwise-valid manifest and asserts
that exactly the expected invariant code appears in the violations.

The VALID_MANIFEST fixture is the minimal correct manifest that passes all checks.
It is intentionally kept small so a mutation can't accidentally fix a pre-existing
problem.
"""

import copy
import pytest
from manifest_schema.linter import ManifestLinter, Violation

# ── Golden valid manifest (minimal) ──────────────────────────────────────────
# This must lint clean — if this fixture itself is invalid, every test below
# will give a false positive.

VALID_MANIFEST: dict = {
    "manifest_id": "test_manifest",
    "schema_version": "1.0",
    "brain_version": "br_1",
    "bitgraph_version": "bg_1",
    "locales": ["en-IN", "hi-IN"],
    "beats": [
        {
            "id": "b_flood",
            "kind": "hold",
            "fact_ids": ["f_wading_depth"],
            "vault_refs": ["plate_flood"],
            "text_slots": {"en-IN": "30 cm of water.", "hi-IN": "30 सेमी पानी।"},
            "audio_slots": {"en-IN": "tts_flood_en"},
            "bindings": [],
            "hinge": {"in": "wide_neutral", "out": "wide_neutral"},
            "edges": [],
        }
    ],
    "edges": [],
    "slots": [],
    "bindings": [],
    "vault": {
        "plate_flood": {
            "kind": "plate",
            "uri": "/assets/plate_flood.jpg",
            "poster_uri": "",
            "depth_uri": "",
            "fact_ids": ["f_wading_depth"],
            "model": "stub",
            "seed": 0,
            "bible_version": "none",
        }
    },
    "accessibility": {"captions": False, "audio_description": False},
    "policy": {"kids_mode": False, "competitor_exclusions": []},
    "integrity": {
        "fact_index": {"f_wading_depth": "sp_001"},
        "beat_index": {"f_wading_depth": ["b_flood"]},
        "asset_index": {"f_wading_depth": ["plate_flood"]},
        "coverage": 1.0,
        "linted_at": "2026-09-30T00:00:00Z",
    },
}


# ── Helper ────────────────────────────────────────────────────────────────────

def _mutate(path: str, value) -> dict:
    """
    Return a deep-copy of VALID_MANIFEST with a single field set to `value`.
    `path` uses dot notation; list indices use [n]; deletion via value=DELETE.
    """
    class _DELETE:
        pass

    m = copy.deepcopy(VALID_MANIFEST)
    parts = path.split(".")
    obj = m
    for part in parts[:-1]:
        if "[" in part:
            key, idx = part.rstrip("]").split("[")
            obj = obj[key][int(idx)]
        else:
            obj = obj[part]
    last = parts[-1]
    if value is _DELETE:
        if "[" in last:
            key, idx = last.rstrip("]").split("[")
            del obj[key][int(idx)]
        else:
            del obj[last]
    else:
        if "[" in last:
            key, idx = last.rstrip("]").split("[")
            obj[key][int(idx)] = value
        else:
            obj[last] = value
    return m

DELETE = type("DELETE", (), {})()

def _codes(violations: list[Violation]) -> list[str]:
    return [v.code for v in violations]

def _has(violations: list[Violation], code: str) -> bool:
    return any(v.code == code for v in violations)


# ── Baseline: valid manifest lints clean ─────────────────────────────────────

def test_valid_manifest_lints_clean():
    """The VALID_MANIFEST fixture must produce zero violations."""
    linter = ManifestLinter(VALID_MANIFEST)
    violations = linter.run()
    assert violations == [], (
        f"VALID_MANIFEST has unexpected violations: {violations}\n"
        "Fix the fixture, not the test."
    )


def test_golden_fixture_lints_clean():
    """The P0 golden fixture (p0_single_beat.json) must lint clean."""
    import json
    from pathlib import Path
    path = Path(__file__).parent.parent / "fixtures" / "p0_single_beat.json"
    manifest = json.loads(path.read_text())
    linter = ManifestLinter(manifest)
    violations = linter.run()
    # Filter _comment — it's allowed as additionalProperties
    assert violations == [], (
        f"p0_single_beat.json has violations: {violations}"
    )


# ── INV-01: schema_version must be '1.0' ─────────────────────────────────────

def test_inv01_wrong_schema_version():
    m = _mutate("schema_version", "2.0")
    violations = ManifestLinter(m).run()
    # schema_version is a JSON Schema `const` — the SCHEMA layer catches it first,
    # which is exactly correct behaviour. Accept either SCHEMA or INV-01.
    assert _has(violations, "INV-01") or _has(violations, "SCHEMA"), (
        f"Expected INV-01 or SCHEMA, got {_codes(violations)}"
    )


def test_inv01_missing_schema_version():
    m = copy.deepcopy(VALID_MANIFEST)
    del m["schema_version"]
    violations = ManifestLinter(m).run()
    # Missing required field → SCHEMA violation (layer 1), not INV-01
    assert _has(violations, "SCHEMA"), f"Expected SCHEMA, got {_codes(violations)}"


# ── INV-02: every beat fact_id in fact_index ──────────────────────────────────

def test_inv02_beat_fact_id_not_in_fact_index():
    m = copy.deepcopy(VALID_MANIFEST)
    m["beats"][0]["fact_ids"] = ["f_unknown_fact"]   # not in integrity.fact_index
    violations = ManifestLinter(m).run()
    assert _has(violations, "INV-02"), f"Expected INV-02, got {_codes(violations)}"


def test_inv02_clean_when_fact_id_present():
    """Adding a matching entry to fact_index must clear the violation."""
    m = copy.deepcopy(VALID_MANIFEST)
    m["beats"][0]["fact_ids"] = ["f_new"]
    m["integrity"]["fact_index"]["f_new"] = "sp_002"
    m["integrity"]["beat_index"]["f_new"] = ["b_flood"]
    m["integrity"]["asset_index"]["f_new"] = ["plate_flood"]
    violations = ManifestLinter(m).run()
    assert not _has(violations, "INV-02"), f"Unexpected INV-02: {violations}"


# ── INV-03: fact_index → beat_index ──────────────────────────────────────────

def test_inv03_fact_in_fact_index_missing_from_beat_index():
    m = copy.deepcopy(VALID_MANIFEST)
    del m["integrity"]["beat_index"]["f_wading_depth"]
    violations = ManifestLinter(m).run()
    assert _has(violations, "INV-03"), f"Expected INV-03, got {_codes(violations)}"


# ── INV-04: fact_index → asset_index ─────────────────────────────────────────

def test_inv04_fact_in_fact_index_missing_from_asset_index():
    m = copy.deepcopy(VALID_MANIFEST)
    del m["integrity"]["asset_index"]["f_wading_depth"]
    violations = ManifestLinter(m).run()
    assert _has(violations, "INV-04"), f"Expected INV-04, got {_codes(violations)}"


# ── INV-05: vault_refs in vault ───────────────────────────────────────────────

def test_inv05_vault_ref_not_in_vault():
    m = copy.deepcopy(VALID_MANIFEST)
    m["beats"][0]["vault_refs"] = ["plate_does_not_exist"]
    violations = ManifestLinter(m).run()
    assert _has(violations, "INV-05"), f"Expected INV-05, got {_codes(violations)}"


def test_inv05_clean_when_vault_ref_present():
    m = copy.deepcopy(VALID_MANIFEST)
    m["beats"][0]["vault_refs"] = ["plate_flood"]   # exists in vault
    violations = ManifestLinter(m).run()
    assert not _has(violations, "INV-05"), f"Unexpected INV-05: {violations}"


# ── INV-06: edge ids from beats exist in edges list ──────────────────────────

def test_inv06_beat_references_nonexistent_edge():
    m = copy.deepcopy(VALID_MANIFEST)
    m["beats"][0]["edges"] = ["e_ghost"]   # not in manifest.edges
    violations = ManifestLinter(m).run()
    assert _has(violations, "INV-06"), f"Expected INV-06, got {_codes(violations)}"


def test_inv06_clean_when_edge_declared():
    m = copy.deepcopy(VALID_MANIFEST)
    m["beats"][0]["edges"] = ["e_flood_spec"]
    m["edges"] = [{
        "id": "e_flood_spec", "from": "b_flood", "to": "b_flood",
        "clip": "", "trigger": "drag_up", "reversible": True,
        "duration_s": 2.0, "label": "Show spec",
    }]
    violations = ManifestLinter(m).run()
    assert not _has(violations, "INV-06"), f"Unexpected INV-06: {violations}"


# ── INV-07: edge endpoints resolve to beat ids ────────────────────────────────

def test_inv07_edge_from_does_not_resolve():
    m = copy.deepcopy(VALID_MANIFEST)
    m["edges"] = [{
        "id": "e_bad", "from": "b_nonexistent", "to": "b_flood",
        "clip": "", "trigger": "auto", "reversible": False,
        "duration_s": 1.0, "label": "",
    }]
    violations = ManifestLinter(m).run()
    assert _has(violations, "INV-07"), f"Expected INV-07, got {_codes(violations)}"


def test_inv07_edge_to_does_not_resolve():
    m = copy.deepcopy(VALID_MANIFEST)
    m["edges"] = [{
        "id": "e_bad", "from": "b_flood", "to": "b_nonexistent",
        "clip": "", "trigger": "auto", "reversible": False,
        "duration_s": 1.0, "label": "",
    }]
    violations = ManifestLinter(m).run()
    assert _has(violations, "INV-07"), f"Expected INV-07, got {_codes(violations)}"


# ── INV-08: hinge labels non-empty ────────────────────────────────────────────

def test_inv08_empty_hinge_in():
    m = copy.deepcopy(VALID_MANIFEST)
    m["beats"][0]["hinge"]["in"] = ""
    violations = ManifestLinter(m).run()
    # minLength:1 on hinge.in is enforced by JSON Schema (layer 1) before INV-08 runs.
    assert _has(violations, "INV-08") or _has(violations, "SCHEMA"), (
        f"Expected INV-08 or SCHEMA, got {_codes(violations)}"
    )


def test_inv08_empty_hinge_out():
    m = copy.deepcopy(VALID_MANIFEST)
    m["beats"][0]["hinge"]["out"] = ""
    violations = ManifestLinter(m).run()
    assert _has(violations, "INV-08") or _has(violations, "SCHEMA"), (
        f"Expected INV-08 or SCHEMA, got {_codes(violations)}"
    )


# ── INV-09: slot beat_id resolves ────────────────────────────────────────────

def test_inv09_slot_beat_id_does_not_resolve():
    m = copy.deepcopy(VALID_MANIFEST)
    m["slots"] = [{
        "id": "slot_1", "beat_id": "b_nonexistent",
        "kind": "shoppable",
        "policy": {"kids_mode": False, "categories_allowed": [], "competitor_exclusions": []},
    }]
    violations = ManifestLinter(m).run()
    assert _has(violations, "INV-09"), f"Expected INV-09, got {_codes(violations)}"


def test_inv09_clean_when_slot_beat_resolves():
    m = copy.deepcopy(VALID_MANIFEST)
    m["slots"] = [{
        "id": "slot_1", "beat_id": "b_flood",   # valid beat
        "kind": "shoppable",
        "policy": {"kids_mode": False, "categories_allowed": [], "competitor_exclusions": []},
    }]
    violations = ManifestLinter(m).run()
    assert not _has(violations, "INV-09"), f"Unexpected INV-09: {violations}"


# ── INV-10: kids_mode → only sponsor_card slots ───────────────────────────────

def test_inv10_kids_mode_with_shoppable_slot():
    m = copy.deepcopy(VALID_MANIFEST)
    m["policy"]["kids_mode"] = True
    m["slots"] = [{
        "id": "slot_1", "beat_id": "b_flood",
        "kind": "shoppable",   # forbidden in kids_mode
        "policy": {"kids_mode": True, "categories_allowed": [], "competitor_exclusions": []},
    }]
    violations = ManifestLinter(m).run()
    assert _has(violations, "INV-10"), f"Expected INV-10, got {_codes(violations)}"


def test_inv10_kids_mode_with_sponsor_card_is_fine():
    m = copy.deepcopy(VALID_MANIFEST)
    m["policy"]["kids_mode"] = True
    m["slots"] = [{
        "id": "slot_1", "beat_id": "b_flood",
        "kind": "sponsor_card",   # allowed in kids_mode
        "policy": {"kids_mode": True, "categories_allowed": [], "competitor_exclusions": []},
    }]
    violations = ManifestLinter(m).run()
    assert not _has(violations, "INV-10"), f"Unexpected INV-10: {violations}"


def test_inv10_non_kids_mode_shoppable_is_fine():
    m = copy.deepcopy(VALID_MANIFEST)
    m["policy"]["kids_mode"] = False
    m["slots"] = [{
        "id": "slot_1", "beat_id": "b_flood",
        "kind": "shoppable",
        "policy": {"kids_mode": False, "categories_allowed": [], "competitor_exclusions": []},
    }]
    violations = ManifestLinter(m).run()
    assert not _has(violations, "INV-10"), f"Unexpected INV-10: {violations}"


# ── INV-13: text_slot locales declared ───────────────────────────────────────

def test_inv13_undeclared_locale_in_text_slots():
    m = copy.deepcopy(VALID_MANIFEST)
    m["beats"][0]["text_slots"]["kn-IN"] = "ಕನ್ನಡ ಪಠ್ಯ"   # kn-IN not in manifest.locales
    violations = ManifestLinter(m).run()
    assert _has(violations, "INV-13"), f"Expected INV-13, got {_codes(violations)}"


def test_inv13_clean_when_locale_declared():
    m = copy.deepcopy(VALID_MANIFEST)
    m["locales"].append("kn-IN")
    m["beats"][0]["text_slots"]["kn-IN"] = "ಕನ್ನಡ ಪಠ್ಯ"
    violations = ManifestLinter(m).run()
    assert not _has(violations, "INV-13"), f"Unexpected INV-13: {violations}"


# ── INV-14: stating beats cite facts; mood beats are explicit ────────────────

def test_inv14_stating_beat_without_facts_fails():
    m = copy.deepcopy(VALID_MANIFEST)
    m["beats"][0]["fact_ids"] = []
    violations = ManifestLinter(m).run()
    assert _has(violations, "INV-14"), f"Expected INV-14, got {_codes(violations)}"


def test_inv14_explicit_mood_beat_without_facts_is_valid():
    m = copy.deepcopy(VALID_MANIFEST)
    m["beats"][0]["fact_ids"] = []
    m["beats"][0]["mood"] = True
    violations = ManifestLinter(m).run()
    assert not _has(violations, "INV-14"), f"Unexpected INV-14: {violations}"


def test_inv14_mood_beat_with_facts_fails():
    m = copy.deepcopy(VALID_MANIFEST)
    m["beats"][0]["mood"] = True
    violations = ManifestLinter(m).run()
    assert _has(violations, "INV-14"), f"Expected INV-14, got {_codes(violations)}"


# ── Schema-level structural violations ───────────────────────────────────────

def test_schema_missing_required_top_level_field():
    m = copy.deepcopy(VALID_MANIFEST)
    del m["beats"]
    violations = ManifestLinter(m).run()
    assert _has(violations, "SCHEMA"), f"Expected SCHEMA, got {_codes(violations)}"


def test_schema_invalid_locale_format():
    m = copy.deepcopy(VALID_MANIFEST)
    m["locales"] = ["english"]   # must match ^[a-z]{2}-[A-Z]{2}$
    violations = ManifestLinter(m).run()
    assert _has(violations, "SCHEMA"), f"Expected SCHEMA, got {_codes(violations)}"


def test_schema_invalid_beat_kind():
    m = copy.deepcopy(VALID_MANIFEST)
    m["beats"][0]["kind"] = "video"   # not in enum
    violations = ManifestLinter(m).run()
    assert _has(violations, "SCHEMA"), f"Expected SCHEMA, got {_codes(violations)}"


def test_schema_invalid_vault_asset_kind():
    m = copy.deepcopy(VALID_MANIFEST)
    m["vault"]["plate_flood"]["kind"] = "video"   # not in enum
    violations = ManifestLinter(m).run()
    assert _has(violations, "SCHEMA"), f"Expected SCHEMA, got {_codes(violations)}"


def test_schema_coverage_out_of_range():
    m = copy.deepcopy(VALID_MANIFEST)
    m["integrity"]["coverage"] = 1.5   # maximum is 1.0
    violations = ManifestLinter(m).run()
    assert _has(violations, "SCHEMA"), f"Expected SCHEMA, got {_codes(violations)}"


def test_schema_missing_locales():
    m = copy.deepcopy(VALID_MANIFEST)
    del m["locales"]
    violations = ManifestLinter(m).run()
    assert _has(violations, "SCHEMA"), f"Expected SCHEMA, got {_codes(violations)}"


# ── Standalone binary exit codes ─────────────────────────────────────────────

def test_linter_binary_exit_0_on_valid(tmp_path):
    import json, subprocess, sys
    manifest_path = tmp_path / "valid.json"
    manifest_path.write_text(json.dumps(VALID_MANIFEST))
    result = subprocess.run(
        [sys.executable, "-m", "manifest_schema.linter", str(manifest_path)],
        capture_output=True, cwd=str(__import__("pathlib").Path(__file__).parent.parent)
    )
    assert result.returncode == 0, result.stderr.decode()


def test_linter_binary_exit_1_on_invalid(tmp_path):
    import json, subprocess, sys
    bad = copy.deepcopy(VALID_MANIFEST)
    bad["schema_version"] = "9.9"
    manifest_path = tmp_path / "bad.json"
    manifest_path.write_text(json.dumps(bad))
    result = subprocess.run(
        [sys.executable, "-m", "manifest_schema.linter", str(manifest_path)],
        capture_output=True, cwd=str(__import__("pathlib").Path(__file__).parent.parent)
    )
    assert result.returncode == 1, "Expected exit code 1 for invalid manifest"


def test_linter_binary_exit_2_on_missing_file(tmp_path):
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "-m", "manifest_schema.linter", str(tmp_path / "does_not_exist.json")],
        capture_output=True, cwd=str(__import__("pathlib").Path(__file__).parent.parent)
    )
    assert result.returncode == 2


def test_linter_strict_mode_fails_below_full_coverage(tmp_path):
    import json, subprocess, sys
    m = copy.deepcopy(VALID_MANIFEST)
    m["integrity"]["coverage"] = 0.9
    manifest_path = tmp_path / "partial.json"
    manifest_path.write_text(json.dumps(m))
    result = subprocess.run(
        [sys.executable, "-m", "manifest_schema.linter", str(manifest_path), "--strict"],
        capture_output=True, cwd=str(__import__("pathlib").Path(__file__).parent.parent)
    )
    assert result.returncode == 1, "Expected exit 1 in strict mode with coverage < 1.0"
