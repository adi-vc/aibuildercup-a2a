"""
brain_store.py — Firestore persistence for Brain records.

Collections (vachan-plan.md §36):
  sources/{source_id}                 Source metadata
  sources/{source_id}/spans/{span_id} Span records
  entities/{entity_id}                Entity records
  facts/{fact_id}                     Fact records
  brain_runs/{run_id}                 BrainRun (pipeline state / gate tracker)
  plays/{play_id}                     signed play records (§36, P7.5)
  playlog_heads/{manifest_id}         {seq, hash} of each manifest's chain head

Indexes written at publish time (vachan-plan.md §24):
  subject → fact_ids:  facts(subject, origin) — stored as subcollection or
                       computed on the fly from a Firestore query (P1 approach).

Design: when FIRESTORE_EMULATOR_HOST is empty and ENV=local we use a simple
in-memory dict store so unit tests run fully offline without a Firestore
project.  The real Firestore client is instantiated only when a live project is
configured.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import Any, Callable

from app.config import settings
from app.models.brain import BrainRun, Entity, Fact, Span, Source, BrainResult

log = logging.getLogger(__name__)


# ── In-memory fallback (no Firestore project needed) ─────────────────────────

class _MemoryStore:
    """Minimal in-memory store used when Firestore is not configured."""

    def __init__(self) -> None:
        self._sources: dict[str, dict] = {}
        self._spans: dict[str, dict[str, dict]] = {}     # source_id → span_id → span
        self._entities: dict[str, dict] = {}
        self._facts: dict[str, dict] = {}
        self._runs: dict[str, dict] = {}
        self._plan_runs: dict[str, dict] = {}
        self._manifests: dict[str, dict] = {}
        self._plays: dict[str, dict] = {}
        self._heads: dict[str, dict] = {}                 # manifest_id → {seq, hash}
        self._chain_lock = threading.Lock()

    # ── Sources ────────────────────────────────────────────────────────────────
    def save_source(self, source: Source) -> None:
        self._sources[source.id] = source.model_dump(mode="json")

    def get_source(self, source_id: str) -> dict | None:
        return self._sources.get(source_id)

    # ── Spans ──────────────────────────────────────────────────────────────────
    def save_span(self, span: Span) -> None:
        self._spans.setdefault(span.source_id, {})[span.id] = span.model_dump()

    def get_spans(self, source_id: str) -> list[dict]:
        return list(self._spans.get(source_id, {}).values())

    # ── Entities ───────────────────────────────────────────────────────────────
    def save_entity(self, entity: Entity) -> None:
        self._entities[entity.id] = entity.model_dump()

    def get_entities(self) -> list[dict]:
        return list(self._entities.values())

    # ── Facts ──────────────────────────────────────────────────────────────────
    def save_fact(self, fact: Fact) -> None:
        self._facts[fact.id] = fact.model_dump()

    def get_fact(self, fact_id: str) -> dict | None:
        return self._facts.get(fact_id)

    def update_fact(self, fact_id: str, updates: dict) -> None:
        if fact_id in self._facts:
            self._facts[fact_id].update(updates)

    def delete_fact(self, fact_id: str) -> None:
        self._facts.pop(fact_id, None)

    def get_facts_by_source(self, source_id: str) -> list[dict]:
        return [f for f in self._facts.values() if f.get("source_id") == source_id]

    def get_facts_by_subject(self, subject: str) -> list[dict]:
        return [f for f in self._facts.values() if f.get("subject") == subject]

    # ── Runs ───────────────────────────────────────────────────────────────────
    def save_run(self, run: BrainRun) -> None:
        self._runs[run.id] = run.model_dump(mode="json")

    def get_run(self, run_id: str) -> dict | None:
        return self._runs.get(run_id)

    def update_run(self, run_id: str, updates: dict) -> None:
        if run_id in self._runs:
            self._runs[run_id].update(updates)

    def get_runs_by_source(self, source_id: str) -> list[dict]:
        return [r for r in self._runs.values() if r.get("source_id") == source_id]

    # ── Planner runs / manifests ─────────────────────────────────────────────
    def save_plan_run(self, run) -> None:
        self._plan_runs[run.id] = run.model_dump(mode="json")

    def get_plan_run(self, run_id: str) -> dict | None:
        return self._plan_runs.get(run_id)

    def update_plan_run(self, run_id: str, updates: dict) -> None:
        if run_id in self._plan_runs:
            self._plan_runs[run_id].update(updates)

    def get_plan_runs_by_source(self, source_id: str) -> list[dict]:
        return [r for r in self._plan_runs.values() if r.get("source_id") == source_id]

    def save_manifest(self, manifest: dict) -> None:
        self._manifests[manifest["manifest_id"]] = manifest

    def get_manifest(self, manifest_id: str) -> dict | None:
        return self._manifests.get(manifest_id)

    # ── Play-log chain ─────────────────────────────────────────────────────────
    def append_play(self, manifest_id: str, seal: Callable[[int, str | None], tuple[dict, str]]) -> dict:
        """Atomically read the chain head, seal the next record against it, advance the head."""
        with self._chain_lock:
            head = self._heads.get(manifest_id)
            record, record_hash = seal(head["seq"] if head else 0, head["hash"] if head else None)
            self._plays[record["play_id"]] = record
            self._heads[manifest_id] = {"seq": record["seq"] + 1, "hash": record_hash}
            return record

    def get_play(self, play_id: str) -> dict | None:
        return self._plays.get(play_id)

    def get_plays_by_manifest(self, manifest_id: str) -> list[dict]:
        return sorted((r for r in self._plays.values() if r["manifest_id"] == manifest_id), key=lambda r: r["seq"])


# ── Firestore backend ─────────────────────────────────────────────────────────

class _FirestoreStore:
    """Thin Firestore wrapper that mirrors the _MemoryStore API."""

    def __init__(self) -> None:
        from google.cloud import firestore
        if settings.firestore_emulator_host:
            os.environ.setdefault(
                "FIRESTORE_EMULATOR_HOST", settings.firestore_emulator_host
            )
        self._db = firestore.Client(project=settings.google_cloud_project)

    # helpers
    def _col(self, *path: str):  # type: ignore[return]
        ref = self._db
        for segment in path:
            ref = ref.collection(segment) if hasattr(ref, "collection") else ref.document(segment)  # type: ignore[attr-defined]
        return ref

    # ── Sources ────────────────────────────────────────────────────────────────
    def save_source(self, source: Source) -> None:
        self._db.collection("sources").document(source.id).set(source.model_dump(mode="json"))

    def get_source(self, source_id: str) -> dict | None:
        doc = self._db.collection("sources").document(source_id).get()
        return doc.to_dict() if doc.exists else None

    # ── Spans ──────────────────────────────────────────────────────────────────
    def save_span(self, span: Span) -> None:
        (
            self._db.collection("sources")
            .document(span.source_id)
            .collection("spans")
            .document(span.id)
            .set(span.model_dump())
        )

    def get_spans(self, source_id: str) -> list[dict]:
        docs = (
            self._db.collection("sources")
            .document(source_id)
            .collection("spans")
            .stream()
        )
        return [d.to_dict() for d in docs]

    # ── Entities ───────────────────────────────────────────────────────────────
    def save_entity(self, entity: Entity) -> None:
        self._db.collection("entities").document(entity.id).set(entity.model_dump())

    def get_entities(self) -> list[dict]:
        return [d.to_dict() for d in self._db.collection("entities").stream()]

    # ── Facts ──────────────────────────────────────────────────────────────────
    def save_fact(self, fact: Fact) -> None:
        self._db.collection("facts").document(fact.id).set(fact.model_dump())

    def get_fact(self, fact_id: str) -> dict | None:
        doc = self._db.collection("facts").document(fact_id).get()
        return doc.to_dict() if doc.exists else None

    def update_fact(self, fact_id: str, updates: dict) -> None:
        self._db.collection("facts").document(fact_id).update(updates)

    def delete_fact(self, fact_id: str) -> None:
        self._db.collection("facts").document(fact_id).delete()

    def get_facts_by_source(self, source_id: str) -> list[dict]:
        return [
            d.to_dict()
            for d in self._db.collection("facts")
            .where("source_id", "==", source_id)
            .stream()
        ]

    def get_facts_by_subject(self, subject: str) -> list[dict]:
        return [
            d.to_dict()
            for d in self._db.collection("facts")
            .where("subject", "==", subject)
            .stream()
        ]

    # ── Runs ───────────────────────────────────────────────────────────────────
    def save_run(self, run: BrainRun) -> None:
        self._db.collection("brain_runs").document(run.id).set(run.model_dump(mode="json"))

    def get_run(self, run_id: str) -> dict | None:
        doc = self._db.collection("brain_runs").document(run_id).get()
        return doc.to_dict() if doc.exists else None

    def update_run(self, run_id: str, updates: dict) -> None:
        self._db.collection("brain_runs").document(run_id).update(updates)

    def get_runs_by_source(self, source_id: str) -> list[dict]:
        return [
            d.to_dict()
            for d in self._db.collection("brain_runs")
            .where("source_id", "==", source_id)
            .stream()
        ]

    # ── Planner runs / manifests ─────────────────────────────────────────────
    def save_plan_run(self, run) -> None:
        self._db.collection("plan_runs").document(run.id).set(run.model_dump(mode="json"))

    def get_plan_run(self, run_id: str) -> dict | None:
        doc = self._db.collection("plan_runs").document(run_id).get()
        return doc.to_dict() if doc.exists else None

    def update_plan_run(self, run_id: str, updates: dict) -> None:
        self._db.collection("plan_runs").document(run_id).update(updates)

    def get_plan_runs_by_source(self, source_id: str) -> list[dict]:
        return [
            d.to_dict() for d in self._db.collection("plan_runs")
            .where("source_id", "==", source_id).stream()
        ]

    def save_manifest(self, manifest: dict) -> None:
        self._db.collection("manifests").document(manifest["manifest_id"]).set(manifest)

    def get_manifest(self, manifest_id: str) -> dict | None:
        doc = self._db.collection("manifests").document(manifest_id).get()
        return doc.to_dict() if doc.exists else None

    # ── Play-log chain ─────────────────────────────────────────────────────────
    def append_play(self, manifest_id: str, seal: Callable[[int, str | None], tuple[dict, str]]) -> dict:
        """Head read + record write + head advance in one transaction, so concurrent plays never fork the chain."""
        from google.cloud import firestore

        head_ref = self._db.collection("playlog_heads").document(manifest_id)

        @firestore.transactional
        def _append(tx):  # type: ignore[no-untyped-def]
            snap = head_ref.get(transaction=tx)
            head = snap.to_dict() if snap.exists else None
            record, record_hash = seal(head["seq"] if head else 0, head["hash"] if head else None)
            tx.set(self._db.collection("plays").document(record["play_id"]), record)
            tx.set(head_ref, {"seq": record["seq"] + 1, "hash": record_hash})
            return record

        return _append(self._db.transaction())

    def get_play(self, play_id: str) -> dict | None:
        doc = self._db.collection("plays").document(play_id).get()
        return doc.to_dict() if doc.exists else None

    def get_plays_by_manifest(self, manifest_id: str) -> list[dict]:
        docs = self._db.collection("plays").where("manifest_id", "==", manifest_id).stream()
        return sorted((d.to_dict() for d in docs), key=lambda r: r["seq"])


# ── Store factory ─────────────────────────────────────────────────────────────

# Module-level singleton — instantiated once per process.
_store: _MemoryStore | _FirestoreStore | None = None


def get_store() -> _MemoryStore | _FirestoreStore:
    global _store
    if _store is None:
        use_firestore = (
            settings.google_cloud_project != "vachan-placeholder"
            or settings.firestore_emulator_host
        )
        if use_firestore:
            try:
                _store = _FirestoreStore()
                log.info("Using Firestore backend (project=%s)", settings.google_cloud_project)
            except Exception as exc:
                log.warning("Firestore init failed (%s) — falling back to in-memory store", exc)
                _store = _MemoryStore()
        else:
            log.info("No GCP project configured — using in-memory store (offline mode).")
            _store = _MemoryStore()
    return _store


def reset_store() -> None:
    """Reset the singleton — used in tests to get a fresh store per test."""
    global _store
    _store = None
