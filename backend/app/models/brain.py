"""
brain.py — Pydantic data models for the Brain (entities, facts, spans, runs).

Three record types (vachan-plan.md §24):
  Entity · Fact · Span

Plus run/gate types used by the build pipeline (§38, §40).

P1: all 8 fixture facts are in STUB_FACTS; real extraction replaces them when
    GEMINI_API_KEY is set.
"""

from __future__ import annotations
from typing import Literal, Any
from pydantic import BaseModel, Field
import datetime
import uuid


# ── Span ─────────────────────────────────────────────────────────────────────

class Span(BaseModel):
    """The literal evidence for a fact — a substring of the source document."""
    id: str
    source_id: str
    start: int
    end: int
    text: str                   # verbatim substring from the source


# ── Entity ───────────────────────────────────────────────────────────────────

EntityType = Literal["Product", "Feature", "Place", "Character", "Concept"]


class Entity(BaseModel):
    id: str
    type: EntityType
    name: str


# ── Fact ─────────────────────────────────────────────────────────────────────

Origin = Literal["canon", "inferred", "imagined"]


class Fact(BaseModel):
    """One checkable statement; the only unit the rest of the system reads."""
    id: str
    subject: str                        # entity id
    predicate: str                      # snake_case_key
    value: str                          # always stored as string; cast at use-site
    unit: str = ""
    text: str                           # one sentence a viewer could read on screen
    origin: Origin = "canon"
    source_id: str = ""
    span_id: str = ""                   # populated after span verification
    # verification metadata (not stored in Firestore top-level, embedded in fact doc)
    verify_method: str = ""             # "exact" | "fuzzy" | "failed" | "stub"
    verify_score: float = 0.0


# ── Source ───────────────────────────────────────────────────────────────────

class Source(BaseModel):
    """Metadata record written when a URL or file is ingested."""
    id: str
    url: str
    checksum: str                       # sha256 of the raw HTML
    fetched_at: datetime.datetime
    gcs_path: str                       # gs://<bucket>/sources/<id>/raw.html
    byte_count: int


# ── Run / Gate ────────────────────────────────────────────────────────────────
# A "run" tracks an async brain-build job through its pipeline steps and gates.

RunStatus = Literal["running", "awaiting_gate", "done", "failed"]

class BrainRun(BaseModel):
    model_config = {"protected_namespaces": ()}
    id: str = Field(default_factory=lambda: f"run_{uuid.uuid4().hex[:12]}")
    source_id: str
    status: RunStatus = "running"
    step: str = "extract"               # current pipeline step label
    coverage: float = 0.0
    entity_count: int = 0
    fact_count: int = 0
    canon_count: int = 0
    inferred_count: int = 0
    model_used: str = ""
    offline: bool = False
    error: str = ""
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


# ── Gate 1 operator payload ───────────────────────────────────────────────────

class FactEdit(BaseModel):
    """Operator correction to a single fact at gate 1."""
    fact_id: str
    field: str          # "value" | "text" | "origin" | "predicate"
    new_value: str


class GateGroundPayload(BaseModel):
    """Body of POST /v1/gates/{run_id}/ground — resumes after gate 1 review."""
    accepts: list[str] = Field(default_factory=list)    # fact_ids to keep as-is
    edits: list[FactEdit] = Field(default_factory=list) # corrections
    drops: list[str] = Field(default_factory=list)      # fact_ids to remove


# ── Brain query result ────────────────────────────────────────────────────────

class BrainResult(BaseModel):
    model_config = {"protected_namespaces": ()}
    source_id: str
    run_id: str
    status: RunStatus
    coverage: float
    entity_count: int
    fact_count: int
    canon_count: int
    inferred_count: int
    model_used: str
    offline: bool
    entities: list[Entity] = Field(default_factory=list)
    facts: list[Fact] = Field(default_factory=list)
    spans: list[Span] = Field(default_factory=list)


# ── Stub facts (P0/offline fallback) ─────────────────────────────────────────
# All 8 facts from vachan-plan.md §17.  Span IDs are placeholders replaced by
# the verifier when it runs against the real source.

STUB_FACTS: list[Fact] = [
    Fact(
        id="f_wading_depth",
        subject="prod_vega_v1",
        predicate="wading_depth",
        value="30", unit="cm",
        text="Wades through water up to 30 cm deep",
        origin="canon", span_id="sp_stub_001",
    ),
    Fact(
        id="f_range",
        subject="prod_vega_v1",
        predicate="range_km",
        value="128", unit="km",
        text="Certified range of 128 km per charge (IDC)",
        origin="canon", span_id="sp_stub_002",
    ),
    Fact(
        id="f_zero_sixty",
        subject="prod_vega_v1",
        predicate="zero_to_sixty_s",
        value="8.2", unit="s",
        text="0–60 km/h in 8.2 seconds",
        origin="canon", span_id="sp_stub_003",
    ),
    Fact(
        id="f_charge_time",
        subject="prod_vega_v1",
        predicate="charge_time_0_80",
        value="4h30m", unit="",
        text="0–80% charge in 4 hours 30 minutes",
        origin="canon", span_id="sp_stub_004",
    ),
    Fact(
        id="f_ground_clearance",
        subject="prod_vega_v1",
        predicate="ground_clearance_mm",
        value="165", unit="mm",
        text="Ground clearance of 165 mm",
        origin="canon", span_id="sp_stub_005",
    ),
    Fact(
        id="offer_price_mumbai",
        subject="prod_vega_v1",
        predicate="offer_price",
        value="129900", unit="INR",
        text="Mumbai on-road price ₹1,29,900",
        origin="canon", span_id="sp_stub_006",
    ),
    Fact(
        id="offer_price_bengaluru",
        subject="prod_vega_v1",
        predicate="offer_price",
        value="127400", unit="INR",
        text="Bengaluru on-road price ₹1,27,400",
        origin="canon", span_id="sp_stub_007",
    ),
    Fact(
        id="warranty",
        subject="prod_vega_v1",
        predicate="battery_warranty",
        value="3yr/30000km", unit="",
        text="3-year or 30,000 km battery warranty",
        origin="canon", span_id="sp_stub_008",
    ),
]
