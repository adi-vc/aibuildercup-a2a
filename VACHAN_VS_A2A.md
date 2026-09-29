# Vachan vs A2A: plan comparison

*As of 2026-09-29*

Vachan and A2A are not two competing ideas: they describe the same engine, and Vachan ([`vachan-plan.md`](vachan-plan.md)) is the later, narrower revision of what the [README](README.md) and `docs_a2a/` call A2A. The engine stays the same; scope, the pitch headline and the build order change.

**Decision (settled):** build **Vachan**, pitch **A2A**. Vachan is what this repo implements; the A2A docs in `docs_a2a/` are the roadmap/vision and deep reference. Rationale and working rules are in [`AGENTS.md`](AGENTS.md).

## At a glance

| | A2A (README + `docs_a2a/`) | Vachan (`vachan-plan.md`) |
| --- | --- | --- |
| Scope | Four live verticals as configs of one engine: Comic, Ads, Education, News | One hero ad demo (+ an optional second ad product, D13); Education, Comic and News become 20-second recorded proofs |
| Headline | A grounded knowledge graph with provenance on every node | The claim guard: the video refuses unsupported claims on screen |
| Brain | Knowledge graph with typed edges, plus `valid_until` expiry on facts | Flat fact rows only (entity, fact, span); no edges, no time-validity layer |
| Changing values (price, stock) | Facts that expire | Bindings looked up at play time: live value, then cached value, then published fact, then neutral wording |
| Added in Vachan | — | Play-log and audit receipt, one-line embed, gesture-scrubbed transitions, kids mode as a schema rule, 5 measured eval metrics, full deck and demo script |
| Build plan | 40 tickets by architecture layer, about 88 ideal days (15–17 weeks solo) | 10 phases (P0–P9) ordered by demo value, with a cut line decided in advance |
| Team split | Backend first, then frontend | Python and TypeScript builders in parallel against a manifest schema frozen in P2 |
| Name | A2A | Vachan (working title), because "A2A" already names the agent-to-agent protocol |

## Three design changes that matter

1. **Flat facts instead of a knowledge graph (decision D11).** Nothing in the system ever traverses the graph: the badge, the claim guard, the linter and rebuilds all look facts up by `subject` or `fact_id`. Typed-edge extraction was cost no viewer sees. The one real graph is the build graph, `fact → beat → asset`, which drives incremental rebuilds.
2. **Bindings replace fact expiry.** A price baked into a video goes stale; a price looked up at play time does not. Each value falls back in a fixed order (live, cached, published fact, neutral wording), so a wrong number is never shown.
3. **One live demo instead of four.** Four live verticals risk reading as four half-demos. One complete Ads demo plus short recordings of the others still proves "one engine", and brings the first demo forward from about day 51 to the first few phases.

## What carries over unchanged

- The core idea: generate persona-neutral media once into a Vault, then compose the video in the browser per viewer from `profile.json`.
- The stack: Python, FastAPI and LangGraph on Cloud Run; Gemini, Veo, Imagen and Chirp TTS on Vertex AI; Firestore and GCS; React, Vite and Remotion on Firebase Hosting.
- Human approval gates between pipeline stages (Vachan trims them to three one-click gates).

[`TECHNICAL_DESIGN.md`](docs_a2a/TECHNICAL_DESIGN.md) stays useful as deep reference for these parts. Skip its typed edges, `valid_until`, News `hub_spoke` and four-vertical config registry until after the demo.

## Where to start building

Build from `vachan-plan.md` (§64), in this order:

1. **P0, walking skeleton.** A deployed `POST /v1/sources` that snapshots a source page to GCS, a hand-written one-beat manifest, and a React page that draws a stock photo with a text layer, served from Firebase Hosting. The goal is to hit deploy, auth and CORS problems on day one.
2. **P2, freeze the manifest schema.** Write `manifest.schema.json`, a linter, and a hand-written golden manifest. This is the only interface between the two builders.
3. **Then two tracks in parallel.** The Python builder does P1 (Brain and span verification) → P3 planner → P4 Vault → P7 claim guard. The TypeScript builder does P5 (runtime, city/language swap, embed) against the golden manifest, without waiting on the pipeline.

The key P1 test: a paraphrased fact injected into the source is demoted to `inferred` automatically, with no human involved.

## Open decisions (from §76)

- [ ] Final name: Vachan, Playtime or Bindu
- [ ] Two or three locales (EN + HI, or also Kannada): sets the "24 vs 36 variants" number in the pitch
- [ ] Keep or cut the Veo hero shot (third on the cut list)
- [ ] Which 4–6 transitions get generated clips (sets the Veo bill)
- [ ] Embed target: storefront block or ad tag
- [ ] Solo build, or two builders on the Python/TypeScript split
