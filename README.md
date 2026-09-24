# A2A — Grounded, Interactive, Personalized Video

> *One source. A living knowledge graph. Infinite personalized, interactive variants — generated once, re-rendered per viewer.*

## What is this?

A2A is an agentic pipeline that turns any source — a product page, a textbook chapter, a news feed, a folk tale — into an **interactive video** that adapts to every viewer, in any language, without re-generating media.

The core insight is a clean split between two very different operations:

- **Generate (expensive, once):** build a small library of persona-neutral media — Gemini-image panels by default, or Veo clips for high-end cinematic output — and store them in a **Vault**.
- **Compose (cheap, per viewer):** assemble the actual video in the browser using Remotion, personalizing text, voice, language, brand skin, and branching on the fly — with zero new generation.

On top of that sits **the Brain**: a grounded knowledge graph of the source where every node links back to a literal span in the original text. Every on-screen claim is auditable. Every variant is traceable.

## The pipeline

```
Source ──▶ Ingest & Ground ──▶ BRAIN (knowledge graph, provenance)
       ──▶ World Enrichment ──▶ personas, benefits, brand skin
       ──▶ Planner ──────────▶ BIT GRAPH (interactive video as a graph of beats + branches)
       ──▶ Vault Builder ────▶ neutral panels/clips in GCS, tagged to Brain nodes
       ──▶ Runtime Player ───▶ profile.json → compose + personalize client-side
```

Each stage is human-gated: a creator can review, edit, or augment every draft before continuing. Nothing reaches render without sign-off.

## Four verticals, one engine

All four demos are configurations of the same pipeline — only the source adapter, graph shape, and interaction pattern differ.

| Demo | Source | Interaction | What's remarkable |
|------|--------|-------------|-------------------|
| **Comic** (Akbar–Birbal) | folk tale / one-line idea | steer the story, ask characters | kids can talk to characters; what-ifs are marked *imagined*; 0 panels redrawn |
| **Ads** (car + earbuds) | product page + brand brief | drill into features | different features surface per viewer (city/household/intent); every claim cited |
| **Education** (history) | textbook chapter | choose your arc | branching "movie" per student; grounded to source line; 0 clips regenerated per student |
| **News** (9 AM bulletin) | live news feeds | dive as deep as you want | fully automated; wiki-style drill-down; generic B-roll reused across days |

The car ad runs in `cinematic` mode (Veo); everything else uses the `panels` default (Gemini-image). One engine, both paths.

## Key properties

- **Generate once, re-render per viewer.** Swapping `profile.json` re-renders instantly — no new media generation.
- **Grounded by default.** Every Brain node carries a source span. Every bit on screen traces back to it. Inferred nodes are flagged.
- **Human-in-the-loop, not autopilot.** The pipeline pauses at each stage; the operator accepts, edits, or feeds in their own input before continuing.
- **Interactive.** The video is a graph, not a timeline. Viewers branch, drill in, and ask questions.
- **Auditable.** Every claim links to its source. Compliance-friendly for regulated verticals.

## Stack

- **Backend:** Python + FastAPI + LangGraph on Cloud Run
- **AI/Media:** Gemini on Vertex AI · Veo · Imagen · Cloud Text-to-Speech (Chirp)
- **Storage:** Firestore · GCS
- **Frontend:** React + TypeScript + Vite + Remotion
- **Hosting:** Firebase Hosting

## Repo layout

```
backend/app/
  agents/          # ingest, enrich, planner (+ per-vertical adapters/patterns)
  vault/           # panels.py (Gemini-image), veo.py, imagen.py, builder.py
  graph/           # brain.py, bitgraph.py
  session/         # manifest pruning, VO/TTS, session API
  expr/            # sandboxed `when` expression language
  binding/         # slot binding → localize → cache
  orchestration/   # LangGraph pipeline + dependency-diff invalidation
  config/          # vertical.config.json for each demo
frontend/src/
  compositions/    # Hook, Feature, Benefit, CTA, BrandCard, Story, News... templates
  player/          # InteractivePlayer (traversal state machine + prefetch)
  studio/          # HITL checkpoint review/edit UI
  grounding/       # GroundingPanel (bit → Brain node → source span)
  profile/         # ProfilePanel (edit profile.json → live re-render)
docs/              # PLAN.md, TECHNICAL_DESIGN.md, BUSINESS_CASE.md, VERTICALS.md
samples/           # fixture sources, seed project (Veo-less, for frontend dev)
```

## Docs

| Doc | Purpose |
|-----|---------|
| [`docs/PLAN.md`](docs/PLAN.md) | Pipeline overview, MVP scope, core concepts. Start here. |
| [`docs/TECHNICAL_DESIGN.md`](docs/TECHNICAL_DESIGN.md) | Full architecture, data model, agent design, `when` grammar, consistency, deployment. |
| [`docs/VERTICALS.md`](docs/VERTICALS.md) | Per-demo specs, interaction patterns, generation economics. |
| [`docs/BUSINESS_CASE.md`](docs/BUSINESS_CASE.md) | Problem, differentiation, target customers, monetization. |
| [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md) | Build sequence, ticket definitions, critical path. Start here to build. |
