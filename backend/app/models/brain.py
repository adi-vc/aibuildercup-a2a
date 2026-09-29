"""
brain.py — Pydantic data models for the Brain (entities, facts, spans).

These are the three record types described in vachan-plan.md §24.
P0: used only as return types; real persistence comes in P1.
"""

from __future__ import annotations
from typing import Literal
from pydantic import BaseModel, Field
import datetime


# ── Span ─────────────────────────────────────────────────────────────────────

class Span(BaseModel):
    """The literal evidence for a fact — a substring of the source document."""
    id: str
    source_id: str
    start: int
    end: int
    text: str


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


# ── Source ───────────────────────────────────────────────────────────────────

class Source(BaseModel):
    """Metadata record written when a URL or file is ingested."""
    id: str
    url: str
    checksum: str                       # sha256 of the raw HTML
    fetched_at: datetime.datetime
    gcs_path: str                       # gs://<bucket>/sources/<id>/raw.html
    byte_count: int


# ── Stub brain (P0 only) ──────────────────────────────────────────────────────

# Hardcoded three-fact stub used by P0 until P1 wires real extraction.
# All three facts are canon and carry placeholder span_ids that P1 will replace.

STUB_FACTS: list[Fact] = [
    Fact(
        id="f_wading_depth",
        subject="prod_vega_v1",
        predicate="wading_depth",
        value="30",
        unit="cm",
        text="Wades through water up to 30 cm deep",
        origin="canon",
        source_id="",   # filled in at runtime once the source is ingested
        span_id="sp_stub_001",
    ),
    Fact(
        id="f_range",
        subject="prod_vega_v1",
        predicate="range_km",
        value="128",
        unit="km",
        text="Certified range of 128 km per charge (IDC)",
        origin="canon",
        source_id="",
        span_id="sp_stub_002",
    ),
    Fact(
        id="f_zero_sixty",
        subject="prod_vega_v1",
        predicate="zero_to_sixty_s",
        value="8.2",
        unit="s",
        text="0–60 km/h in 8.2 seconds",
        origin="canon",
        source_id="",
        span_id="sp_stub_003",
    ),
]
