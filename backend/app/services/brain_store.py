"""
brain_store.py — Firestore persistence for Brain records.

Collections (vachan-plan.md §36):
  sources/{source_id}                 Source metadata
  sources/{source_id}/spans/{span_id} Span records
  entities/{entity_id}                Entity records
  facts/{fact_id}                     Fact records
  brain_runs/{run_id}                 BrainRun (pipeline state / gate tracker)

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
from typing import Any

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
