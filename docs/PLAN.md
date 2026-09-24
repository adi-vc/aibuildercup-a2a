# A2A — Interactive Video Personalization Harness (Plan / Overview)

## Context

We're building an **agentic AI harness that turns any source (starting with a product page + brand brief) into an *interactive* video** — not sequential frames, but a **graph of "bits" that open up on demand and re-render per viewer**.

A plain "source → video converter" produces one linear artifact with no memory and no provenance. This system does two things a converter cannot:

1. **Stores the world in a living knowledge graph (the "Brain")** — spokespeople (look, voice, personality), places/cities, dated events, product features, brand facts — where **every node points back to a span in the source** (grounding/provenance).
2. **Assembles video on the fly by traversing a generation graph**, composing personalized bits per persona/language/city, so a finite generated corpus yields effectively infinite grounded variants.

## Anchor decisions

- **Scope:** thin end-to-end MVP + roadmap (hackathon).
- **Verticals:** **four MVP build targets** — *Comic* (Demo 0: kids' entertainment — Akbar–Birbal, "a comic you can talk to"), *product Ads* (a **car** and an **earbuds** ad, feature-router), *Education* (branching history movie, character-consistent), and *News* (self-assembling daily bulletin, hub-and-spoke + procedural deepening) — each a configuration of the same engine (full specs in [`VERTICALS.md`](./VERTICALS.md)). Ads is the primary worked example throughout this doc; the pipeline is vertical-agnostic.
- **Workflow model — human-in-the-loop, not full autopilot:** the harness is agentic and automates the heavy lifting, but a human can **review, edit, and approve at every stage** (source → Brain → storyboard/Bit Graph → Vault) and inject their own input — storyboard beats, which features go in the Vault, character ideas, seed images, copy. Nothing proceeds to the next stage without (implicit or explicit) sign-off. This avoids the common failure mode where a fully-autonomous pipeline produces a polished-but-wrong final video that gets scrapped or needs heavy rework.
- **Video engine (the crux) — generate once, render on the viewer's device:**
  - **Default (`panels`):** **Gemini-image** keyframe panels ("Nano Banana") are generated once into a **Vault** and **animated on-device** by the runtime — cheapest, most character-consistent, "0 images redrawn" across every variant.
  - **High-end (`cinematic`):** **Google Veo** clips instead — an opt-in path for filmic fidelity (e.g. ad-production agencies; the **car** ad demo runs `cinematic` to showcase it). `media_mode` is a per-project override on the vertical default.
  - **Remotion-style client-side canvas runtime** does the **programmatic composition & personalization** (overlays, captions, localized VO, brand skin, data-driven animation, branch UI) — cheap, instant, per-context.
- **Personalization input:** driven by an **editable `profile.json`** (e.g. `location`, `age_bracket`, `household`, `language`, `intent`). We are **not** building profile selection or inference in the MVP — the operator edits the JSON for their demo audience and the video **re-renders on the fly** to surface the most relevant features/story.
- **Stack:** Python + FastAPI backend, React/TS + Remotion web player, Google model/hosting stack (Gemini on Vertex AI, Veo, Imagen, Cloud Text-to-Speech/Chirp, GCS, Cloud Run / Firebase Hosting).

## Core concepts

- **Source** — any input; MVP: a product-page URL (+ optional brand brief), for two products (a car, earbuds).
- **Brain (Knowledge Graph)** — the living world model. Every node carries `provenance` → source span(s).
- **Vault** — persona-neutral generated media: **Gemini-image panels by default** (Veo clips for high-end `cinematic`; Imagen stills), tagged with the Brain nodes they depict, so one asset serves many personas. Cached in GCS.
- **Generation Graph (Bit Graph)** — the interactive video itself; nodes are **Bits** (a beat/panel), edges are transitions (`default_next`, `user_choice`, `personalization_conditional`). Profile-conditional edges are how the *same* ad shows *different* features to different viewers.
- **Profile (`profile.json`)** — the Personalization Context as an editable file: `{ location, age_bracket, household, language, intent, … }`. Editing it re-renders the video on the fly. No selection/inference UI in the MVP.
- **Studio (human-in-the-loop surface)** — the review/edit UI at each pipeline checkpoint; where the operator accepts, edits, or augments each agent draft (beats, features, characters, seed images) before continuing.
- **Runtime Player** — React + Remotion; plays bits, selects feature bits from the profile, renders branch/drill-down UI, prefetches & **materializes the next bits on the fly**.
- **Talk to it · canon vs imagined · time-aware:** viewers can **ask a character** (grounded answers, claim-guarded, TECH §4.6); "what-if" branches are marked **imagined** (`veracity`); facts can **expire** (`valid_until`) which powers self-updating News (TECH §3.1).

**Why this is not a converter:** grounding (auditable claims, compliance-friendly ads); a reusable living graph (edit source → all videos regenerate); traversal-time composition (infinite personalized variants, zero re-generation); and a **human-in-the-loop** authoring flow that keeps creative control instead of emitting take-it-or-leave-it output.

## The agentic pipeline (with human-in-the-loop checkpoints)

```
Source ──▶ (1) Ingest & Ground [Gemini] ──▶ BRAIN (graph, provenance→source spans)   ⏸ review/edit
        ──▶ (2) World enrichment [Gemini] ── personas, benefits, brand skin, spokesperson  ⏸ review/edit
        ──▶ (3) Generation-graph planner [Gemini agent] ──▶ BIT GRAPH (beats + branches)   ⏸ review/edit
        ──▶ (4) Vault acquisition [Gemini-image panels (default) / Veo / Imagen] ── neutral media tagged to Brain nodes (GCS) ⏸ review/approve
        ──▶ (5) RUNTIME PLAYER [React+Remotion] ◀── profile.json (Personalization Context)
              bind persona text + localized VO (Cloud TTS) + brand skin → composite client-side
              select feature bits on the fly from the profile; at branch points materialize next bits
```

At each ⏸ checkpoint the operator can accept the draft, edit it, or add their own input (beats, features, characters, seed images) before the agent continues. Stages 1–4 are backend/cached and human-gated; stage 5 is the interactive client. **Personalization and interactivity happen at composition time, not generation time** — swapping `profile.json` re-renders instantly with no new generation.

## MVP scope (thin slice — four verticals)

Goal: **paste a source → step through the agent stages (reviewing/editing each) → get an interactive video that re-renders on the fly when you edit `profile.json`.** All four verticals ship: **Comic** (Akbar–Birbal), **Ads** (car + earbuds), **Education**, **News** — each a `vertical.config.json` over the same pipeline (see [`VERTICALS.md`](./VERTICALS.md)). The Ads walkthrough below is the canonical example; Comic adds character-consistent panels + ask-a-character, Education adds character-consistent Vault + branch-explore, News adds a scheduled run, persistent incremental Brain, reuse/lazy Vault, and procedural deepening.

1. **Ingest + ground** (Gemini) → Brain JSON: product, ~4–6 features→benefits, brand style, 2 personas, 2 languages, 2 cities; each node stores its source span. ⏸ operator reviews/edits the extracted graph.
2. **Plan bit graph** (Gemini) → ~6–10 bits with **profile-conditional feature bits** + 1–2 user-choice drill-downs. ⏸ operator reviews/edits the storyboard (reorder beats, drop/add features, add a beat).
3. **Vault** (Gemini-image **panels** by default; Veo/Imagen for cinematic) → ~5–8 neutral panels/clips/stills, tagged to Brain nodes, GCS (pre-generated for demo reliability). ⏸ operator picks which features get media / supplies seed images.
4. **Remotion runtime** → templates (Hook, Feature, Benefit, City/Offer, CTA) compositing vault clip + persona text + localized VO + captions + brand skin.
5. **Player UI** → an **editable `profile.json` panel**: change `location`/`age_bracket`/`household`/`language` and watch the ad **re-render with the most relevant features** (see the worked example below); clickable branch to drill into a feature; a **grounding panel** (hover a bit → source span).

**All demo specs (Comic, Ads car/earbuds, Education, News) and their concrete parameters live in [`VERTICALS.md`](./VERTICALS.md).** The pipeline above is vertical-agnostic — a demo is just a configuration of it (see the core parameterization in [`TECHNICAL_DESIGN.md`](./TECHNICAL_DESIGN.md) §2.2).

**Out of MVP (→ roadmap):** *blocking* live Veo during playback (News lazy generation **is** in MVP, but non-blocking — placeholder now, Veo generated in the background; see [`TECHNICAL_DESIGN.md`](./TECHNICAL_DESIGN.md) §4.4–§4.5), full **entity resolution** (MVP merges multi-day/multi-article sources by key-based upsert), unbounded procedural depth beyond the configured max, `pov_lens` narration variants, graph DB, and **automatic** profile/persona inference (MVP uses a hand-edited `profile.json`).

## Repository layout (all new)

```
video-hackathon/
├─ docs/                            # this file, TECHNICAL_DESIGN.md, BUSINESS_CASE.md
├─ backend/                         # Python + FastAPI on Cloud Run
│  ├─ app/main.py                   # /ingest, /plan, /vault, /session
│  ├─ app/agents/{ingest,enrich,planner}.py
│  ├─ app/vault/panels.py, veo.py   # panels(default)/Veo/Imagen gen + GCS store
│  ├─ app/graph/{brain,bitgraph}.py
│  └─ app/models.py                 # pydantic schemas
├─ frontend/                        # React + TS + Vite + Remotion
│  ├─ src/player/InteractivePlayer.tsx
│  ├─ src/compositions/             # Hook/Feature/Benefit/CTA templates
│  ├─ src/personalize/context.ts
│  └─ src/grounding/GroundingPanel.tsx
├─ samples/
└─ README.md
```

## Roadmap (beyond MVP)

- Lazy/live Veo with vault cache + consistency anchors; procedural branch expansion ("worlds open up as you go deeper").
- Multi-source ingestion (PDF, image, comic, news) + entity resolution → same engine powers comic-world and education verticals.
- Viewer-signal persona inference, A/B, analytics feeding the graph.
- Graph DB (Neo4j / Spanner Graph) + vector index for retrieval-grounding.
- Compliance export: provenance report per rendered ad.

## Verification / demo

1. Backend: `POST /ingest` a product URL → Brain JSON with real `provenance.span` per node.
2. Vault: build → Veo clips + Imagen stills in GCS, tagged to node ids.
3. Planner: `POST /plan` → Bit Graph with ≥1 branch point, every bit grounded.
4. Player: switch persona/language/city live → recomposes; drill into a feature; hover → grounding panel shows source span.
5. Full loop: product URL in → interactive personalized video out, provenance visible for every bit.

---
*Companion docs: [`TECHNICAL_DESIGN.md`](./TECHNICAL_DESIGN.md) · [`BUSINESS_CASE.md`](./BUSINESS_CASE.md) · [`VERTICALS.md`](./VERTICALS.md)*
