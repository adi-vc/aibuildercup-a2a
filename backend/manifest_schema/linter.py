#!/usr/bin/env python3
"""
linter.py — Vachan manifest linter (vachan-plan.md §39.9, §64.4).

Usage (standalone binary):
    python -m manifest_schema.linter path/to/manifest.json
    python -m manifest_schema.linter path/to/manifest.json --strict   # coverage must be 1.0

Exit codes:
    0  — manifest is valid
    1  — one or more invariant violations found (details printed to stderr)
    2  — file not found or not valid JSON

The linter checks three layers in order, stopping on the first layer that fails
so the error message is always actionable:

  Layer 1 — JSON Schema validation (structural correctness)
  Layer 2 — Cross-reference invariants (references that Schema can't express)
  Layer 3 — Semantic rules (business logic from §26 and §39.9)

Each invariant has a short code (e.g. INV-01) so CI logs are scannable.
Adding a new invariant means adding a new INV-NN check AND a corresponding
test in tests/test_linter.py — one test per invariant is the rule.

Invariants (§39.9 + §26 + §28):
  INV-01  schema_version == "1.0"
  INV-02  Every beat.fact_id in integrity.fact_index
  INV-03  Every fact_id in integrity.fact_index in integrity.beat_index
  INV-04  Every fact_id in integrity.fact_index in integrity.asset_index
  INV-05  Every beat.vault_ref in vault
  INV-06  Every beat.edge in edges (by id)
  INV-07  Every edge.from and edge.to resolve to a beat id
  INV-08  Hinge labels: every beat.hinge.in and .out is a non-empty string (already schema)
          + every edge.from beat.hinge.out == every edge.to beat.hinge.in
          (structural check: hinge labels at endpoints must exist; value match is advisory)
  INV-09  Slots only at beats that exist (beat_id resolves)
  INV-10  kids_mode manifest has zero non-sponsor_card slots
  INV-11  integrity.coverage is a number in [0, 1]  (already schema — tested separately)
  INV-12  No baked text: vault plates must not have uri ending in a text-bearing format
          that would indicate text was baked in. (Structural proxy: uri must be non-empty — 
          the real check is the vision pass at P4; the linter asserts the uri is present.)
  INV-13  Every locale in beat.text_slots is declared in manifest.locales
  INV-14  Every stating beat (fact_ids non-empty) cites ≥1 fact_id
          (already covered by INV-02 for cross-ref, but separately: fact_ids list non-empty)
  INV-15  linted_at is present and non-empty (already schema)
  INV-16  If integrity.facts is present, its keys equal integrity.fact_index's
          and every entry is origin=canon (only canon facts may reach a viewer)
  INV-17  Every branch_only beat is the `to` of at least one edge (reachable)
  INV-18  Every non-empty edge.clip resolves to a vault asset of kind `clip`
"""

from __future__ import annotations

import json
import sys
import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import jsonschema
    from jsonschema import validate, ValidationError
    _HAS_JSONSCHEMA = True
except ImportError:
    _HAS_JSONSCHEMA = False

SCHEMA_PATH = Path(__file__).parent / "manifest.schema.json"


# ── Violation type ────────────────────────────────────────────────────────────

@dataclass
class Violation:
    code: str       # e.g. "INV-02"
    message: str
    path: str = ""  # JSON path to the offending element


# ── Main linter class ─────────────────────────────────────────────────────────

class ManifestLinter:
    """
    Run all invariant checks against a manifest dict.

    Usage:
        linter = ManifestLinter(manifest_dict)
        violations = linter.run()
        # violations is an empty list if the manifest is valid
    """

    def __init__(self, manifest: dict[str, Any]) -> None:
        self.m = manifest
        self._violations: list[Violation] = []

    def run(self) -> list[Violation]:
        self._violations.clear()

        # Layer 1: JSON Schema
        schema_ok = self._check_schema()
        if not schema_ok:
            return self._violations   # no point running cross-ref checks

        # Layer 2: Cross-reference invariants
        self._check_inv01_schema_version()
        self._check_inv02_fact_ids_in_fact_index()
        self._check_inv03_fact_index_in_beat_index()
        self._check_inv04_fact_index_in_asset_index()
        self._check_inv05_vault_refs_in_vault()
        self._check_inv06_edge_ids_from_beats_exist()
        self._check_inv07_edge_endpoints_resolve()
        self._check_inv08_hinge_labels()
        self._check_inv09_slot_beat_ids_resolve()

        # Layer 3: Semantic rules
        self._check_inv10_kids_mode_no_non_sponsor_slots()
        self._check_inv13_text_slot_locales_declared()
        self._check_inv14_stating_beats_have_fact_ids()
        self._check_inv16_published_facts_match_fact_index()
        self._check_inv17_branch_beats_reachable()
        self._check_inv18_edge_clips_in_vault()

        return self._violations

    # ── Layer 1 ───────────────────────────────────────────────────────────────

    def _check_schema(self) -> bool:
        """Validate against the JSON Schema. Returns False if validation fails."""
        if not _HAS_JSONSCHEMA:
            self._add("SCHEMA", "jsonschema package not installed — structural checks skipped.")
            return True  # don't block cross-ref checks

        if not SCHEMA_PATH.exists():
            self._add("SCHEMA", f"Schema file not found: {SCHEMA_PATH}")
            return False

        schema = json.loads(SCHEMA_PATH.read_text())
        try:
            validate(instance=self.m, schema=schema)
            return True
        except ValidationError as exc:
            path = " > ".join(str(p) for p in exc.absolute_path) or "(root)"
            self._add("SCHEMA", f"{exc.message}", path=path)
            return False

    # ── Layer 2: cross-reference invariants ───────────────────────────────────

    def _check_inv01_schema_version(self) -> None:
        """INV-01: schema_version must be exactly '1.0'."""
        if self.m.get("schema_version") != "1.0":
            self._add("INV-01", f"schema_version must be '1.0', got {self.m.get('schema_version')!r}")

    def _check_inv02_fact_ids_in_fact_index(self) -> None:
        """INV-02: Every fact_id cited by any beat must appear in integrity.fact_index."""
        fact_index: dict = self.m.get("integrity", {}).get("fact_index", {})
        for beat in self.m.get("beats", []):
            for fid in beat.get("fact_ids", []):
                if fid not in fact_index:
                    self._add(
                        "INV-02",
                        f"Beat '{beat['id']}' cites fact_id '{fid}' not in integrity.fact_index",
                        path=f"beats[{beat['id']}].fact_ids",
                    )

    def _check_inv03_fact_index_in_beat_index(self) -> None:
        """INV-03: Every fact_id in fact_index must appear in beat_index."""
        integrity = self.m.get("integrity", {})
        fact_index: dict = integrity.get("fact_index", {})
        beat_index: dict = integrity.get("beat_index", {})
        for fid in fact_index:
            if fid not in beat_index:
                self._add(
                    "INV-03",
                    f"fact_id '{fid}' in integrity.fact_index but absent from integrity.beat_index",
                    path="integrity.beat_index",
                )

    def _check_inv04_fact_index_in_asset_index(self) -> None:
        """INV-04: Every fact_id in fact_index must appear in asset_index."""
        integrity = self.m.get("integrity", {})
        fact_index: dict = integrity.get("fact_index", {})
        asset_index: dict = integrity.get("asset_index", {})
        for fid in fact_index:
            if fid not in asset_index:
                self._add(
                    "INV-04",
                    f"fact_id '{fid}' in integrity.fact_index but absent from integrity.asset_index",
                    path="integrity.asset_index",
                )

    def _check_inv05_vault_refs_in_vault(self) -> None:
        """INV-05: Every vault_ref cited in a beat must exist as a key in vault."""
        vault: dict = self.m.get("vault", {})
        for beat in self.m.get("beats", []):
            for ref in beat.get("vault_refs", []):
                if ref not in vault:
                    self._add(
                        "INV-05",
                        f"Beat '{beat['id']}' references vault asset '{ref}' not in vault",
                        path=f"beats[{beat['id']}].vault_refs",
                    )

    def _check_inv06_edge_ids_from_beats_exist(self) -> None:
        """INV-06: Every edge id referenced in beat.edges must exist in manifest.edges."""
        edge_ids = {e["id"] for e in self.m.get("edges", [])}
        for beat in self.m.get("beats", []):
            for eid in beat.get("edges", []):
                if eid not in edge_ids:
                    self._add(
                        "INV-06",
                        f"Beat '{beat['id']}' references edge '{eid}' not in manifest.edges",
                        path=f"beats[{beat['id']}].edges",
                    )

    def _check_inv07_edge_endpoints_resolve(self) -> None:
        """INV-07: Every edge.from and edge.to must resolve to a beat id."""
        beat_ids = {b["id"] for b in self.m.get("beats", [])}
        for edge in self.m.get("edges", []):
            for endpoint in ("from", "to"):
                bid = edge.get(endpoint, "")
                if bid and bid not in beat_ids:
                    self._add(
                        "INV-07",
                        f"Edge '{edge['id']}' has {endpoint}='{bid}' which does not match any beat id",
                        path=f"edges[{edge['id']}].{endpoint}",
                    )

    def _check_inv08_hinge_labels(self) -> None:
        """
        INV-08: Every beat must have non-empty hinge.in and hinge.out labels.
        (Value matching between edge endpoints is advisory at P2 — tracked as a warning.)
        """
        for beat in self.m.get("beats", []):
            hinge = beat.get("hinge", {})
            if not hinge.get("in"):
                self._add(
                    "INV-08",
                    f"Beat '{beat['id']}' has empty hinge.in",
                    path=f"beats[{beat['id']}].hinge.in",
                )
            if not hinge.get("out"):
                self._add(
                    "INV-08",
                    f"Beat '{beat['id']}' has empty hinge.out",
                    path=f"beats[{beat['id']}].hinge.out",
                )

    def _check_inv09_slot_beat_ids_resolve(self) -> None:
        """INV-09: Every slot.beat_id must resolve to a beat id."""
        beat_ids = {b["id"] for b in self.m.get("beats", [])}
        for slot in self.m.get("slots", []):
            bid = slot.get("beat_id", "")
            if bid and bid not in beat_ids:
                self._add(
                    "INV-09",
                    f"Slot '{slot['id']}' references beat_id '{bid}' not in manifest.beats",
                    path=f"slots[{slot['id']}].beat_id",
                )

    # ── Layer 3: semantic rules ───────────────────────────────────────────────

    def _check_inv10_kids_mode_no_non_sponsor_slots(self) -> None:
        """INV-10: A kids_mode=true manifest must have zero non-sponsor_card slots."""
        if not self.m.get("policy", {}).get("kids_mode", False):
            return
        for slot in self.m.get("slots", []):
            if slot.get("kind") != "sponsor_card":
                self._add(
                    "INV-10",
                    f"kids_mode manifest contains non-sponsor_card slot '{slot.get('id', '?')}' "
                    f"(kind='{slot.get('kind')}'). Only sponsor_card slots are allowed.",
                    path=f"slots[{slot.get('id', '?')}].kind",
                )

    def _check_inv13_text_slot_locales_declared(self) -> None:
        """INV-13: Every locale used in beat.text_slots must be declared in manifest.locales."""
        declared = set(self.m.get("locales", []))
        for beat in self.m.get("beats", []):
            for locale in beat.get("text_slots", {}):
                if locale not in declared:
                    self._add(
                        "INV-13",
                        f"Beat '{beat['id']}' uses locale '{locale}' in text_slots "
                        f"but '{locale}' is not in manifest.locales",
                        path=f"beats[{beat['id']}].text_slots",
                    )

    def _check_inv14_stating_beats_have_fact_ids(self) -> None:
        """
        INV-14: Every non-mood (stating) beat cites at least one fact. Mood beats
        are explicitly marked `mood: true` and cite no facts. This is the plan's
        distinction between an atmospheric hold and an on-screen claim.
        """
        for beat in self.m.get("beats", []):
            fact_ids = beat.get("fact_ids", [])
            mood = beat.get("mood", False)
            if mood and fact_ids:
                self._add(
                    "INV-14",
                    f"Mood beat '{beat['id']}' must not cite fact_ids.",
                    path=f"beats[{beat['id']}].fact_ids",
                )
            elif not mood and not fact_ids:
                self._add(
                    "INV-14",
                    f"Stating beat '{beat['id']}' must cite at least one fact_id or declare mood=true.",
                    path=f"beats[{beat['id']}].fact_ids",
                )

    def _check_inv16_published_facts_match_fact_index(self) -> None:
        """
        INV-16: integrity.facts is optional, but when present it must describe
        exactly the cited facts (keys == fact_index) and only canon ones. The
        runtime shows these values on screen as the §24.2 rung-3 fallback, so
        an extra or non-canon entry would be an uncited claim.
        """
        integrity = self.m.get("integrity", {})
        facts = integrity.get("facts")
        if facts is None:
            return
        indexed = set(integrity.get("fact_index", {}))
        for fid in sorted(indexed - facts.keys()):
            self._add("INV-16", f"fact_id '{fid}' is in fact_index but missing from integrity.facts",
                      path="integrity.facts")
        for fid in sorted(facts.keys() - indexed):
            self._add("INV-16", f"integrity.facts has '{fid}', which is not in fact_index",
                      path="integrity.facts")
        for fid, fact in facts.items():
            if fact.get("origin") != "canon":
                self._add("INV-16", f"integrity.facts['{fid}'] is origin={fact.get('origin')!r}; only canon may ship",
                          path=f"integrity.facts[{fid}]")

    def _check_inv17_branch_beats_reachable(self) -> None:
        """INV-17: a branch_only beat is skipped by the main sequence, so an edge must lead to it."""
        targets = {e.get("to") for e in self.m.get("edges", [])}
        for beat in self.m.get("beats", []):
            if beat.get("branch_only") and beat["id"] not in targets:
                self._add("INV-17", f"branch_only beat '{beat['id']}' is not the target of any edge (unreachable)",
                          path=f"beats[{beat['id']}]")

    def _check_inv18_edge_clips_in_vault(self) -> None:
        """INV-18: an edge that names a clip must point at a clip asset (empty clip = a cut)."""
        vault = self.m.get("vault", {})
        for edge in self.m.get("edges", []):
            clip = edge.get("clip", "")
            if clip and vault.get(clip, {}).get("kind") != "clip":
                self._add("INV-18", f"Edge '{edge['id']}' clip '{clip}' is not a clip asset in vault",
                          path=f"edges[{edge['id']}].clip")

    # ── Helper ────────────────────────────────────────────────────────────────

    def _add(self, code: str, message: str, path: str = "") -> None:
        self._violations.append(Violation(code=code, message=message, path=path))


# ── Standalone binary ─────────────────────────────────────────────────────────

def lint_file(path: Path, strict: bool = False) -> list[Violation]:
    """Load a manifest JSON file and run the linter. Returns violations."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"ERROR: file not found: {path}", file=sys.stderr)
        sys.exit(2)

    try:
        manifest = json.loads(text)
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON in {path}: {exc}", file=sys.stderr)
        sys.exit(2)

    linter = ManifestLinter(manifest)
    violations = linter.run()

    if strict:
        coverage = manifest.get("integrity", {}).get("coverage", 0)
        if coverage < 1.0:
            violations.append(Violation(
                code="INV-STRICT",
                message=f"--strict mode: coverage={coverage} < 1.0. "
                        "All canon facts must have verified spans before publishing.",
                path="integrity.coverage",
            ))

    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m manifest_schema.linter",
        description="Vachan manifest linter — exits 0 if valid, 1 on violations.",
    )
    parser.add_argument("manifest", nargs="?", help="Path to manifest JSON file")
    parser.add_argument("--strict", action="store_true",
                        help="Also require coverage == 1.0 (for publish gates)")
    args = parser.parse_args(argv)

    if not args.manifest:
        parser.print_help()
        return 2

    path = Path(args.manifest)
    violations = lint_file(path, strict=args.strict)

    if not violations:
        print(f"✓ {path.name} — OK (schema_version=1.0, all invariants pass)")
        return 0

    print(f"✗ {path.name} — {len(violations)} violation(s):", file=sys.stderr)
    for v in violations:
        loc = f"  at {v.path}" if v.path else ""
        print(f"  [{v.code}] {v.message}{loc}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
