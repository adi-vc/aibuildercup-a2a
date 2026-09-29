# Vachan — Grounded, Interactive, Personalized Video

> **Paste a source. You get an interactive video that assembles itself for every viewer — language, city, price, and the questions they ask — and that cannot say anything the source doesn't support.**

Vachan is a **runtime, not a renderer.** Media is generated *once*, persona-neutral; the video is *composed in the browser, per viewer.* On top sits a grounded fact layer where every on-screen claim traces to a literal span of the source — so the video is personalized at scale, interactive, **and** auditable at the same time. Nothing on the market is all three.

---

## The idea in three claims

1. **Generated once, composed per viewer.** Many variants, zero new media. Cost is `O(assets)`, not `O(viewers)` — a different business, not a better feature.
2. **True when you press play.** Price, stock and offer resolve live at play-time, so nothing is stale the day a value changes.
3. **It cannot over-claim, and it proves what it showed.** Every beat and answer is drawn from a fact carrying a string-verified source span; anything unsupported is **refused on screen**, and a signed play-log records exactly what each viewer saw.

## The mechanism (the moment that lands in 8 seconds)

> **Viewer:** "Is it the fastest in India?"
> **Character:** "I can only tell you what's verified: 0–60 in 8.2 seconds, from the spec sheet."

This is **the claim guard.** Grounding/provenance is the machinery that makes the refusal possible; the refusal is what anyone repeats in one sentence — *"the ad that can't lie."*

---

## The problem it solves

- **Video is priced per artifact.** One product film means an agency, a crew, an edit — then multiply by every product, market and language.
- **Personalization is combinatorics.** 12 cities × 3 languages × 2 personas = 72 renders to commission, store, version and re-shoot.
- **Everything you render is stale on arrival.** The price changed, the variant sold out, the offer expired.
- **Generated marketing over-claims.** A model told to "make it exciting" invents a spec — a liability in any regulated category.

**The gap:** no system makes video personalized-at-scale, interactive, *and* provably grounded. That gap is the whole opportunity.

## The insight

|  | Generate | Compose |
|---|---|---|
| Cost | Expensive | Nearly free |
| When | Once, ahead of time | The moment someone presses play |
| Produces | Persona-neutral media | The video *this* viewer sees |
| Varies with | Nothing | Language, city, price, persona, choices |

Everyone fuses generation and composition into one baked file. Split them, and per-viewer variation stops costing anything.

## Why this isn't a video generator — and why it's hard to copy

Generative-video tools (Veo, Runway, Kling, Sora) produce *clips* — one file, identical for everyone, stale on change, ungrounded. Vachan **uses** such a model as one build-time component and adds what a clip can never have. The video model is a swappable part; the value is the grounded, composable, auditable layer above it. **Short the model, long the graph** — falling model prices are a tailwind, not a threat.

|  | Generative video | Template / personalized-video tools | Agentic builders | **Vachan** |
|---|---|---|---|---|
| Beautiful clips | ✅ | ✅ | partly | ✅ *(not the point)* |
| Composed per viewer at play-time | ❌ | ❌ | ❌ | **✅** |
| Live values inside the content | ❌ | ❌ | ❌ | **✅** |
| Grounded per claim, refuses the unsupported | ❌ | ❌ | ❌ | **✅** |
| Receipt of exactly what was shown | ❌ | ❌ | ❌ | **✅** |
| Scenes authored by | a prompt | a human on a canvas | a prompt | **the source document** |

The clip, the interactivity and the personalization are all copyable. **Grounding is not** — it is a knowledge-first approach, orthogonal to what pixel-first tools are built to do. An incumbent that wants to match it has to build the grounded fact layer underneath — and that's a different product.

## Where this goes — one engine, many industries

The same ingest → ground → compose engine, specialized only by its source adapter and templates, turns *any* static content into grounded, interactive, per-viewer video. Each target below is a large industry on its own:

| Domain | Static content becomes… | Why only this engine can |
|---|---|---|
| **Advertising** (~$1T) | a product page → an ad that shows different features to different viewers, every claim cited | per-viewer composition + ad-compliance provenance |
| **Education** (~$300B+) | a chapter → a branching "movie" a student steers, grounded to the textbook line | re-rendered per student, never regenerated; teacher-trustable |
| **News / media** (~$100B+) | live feeds → a self-assembling briefing you drill into like a wiki, every claim cited | live values + refusal replace the human editor |
| **Kids' stories** | a folk tale → a comic children can *talk to*, what-ifs clearly marked imagined | grounded, safe, ad-free by construction |
| **Regulated explainers** (insurance · finance · health) | a policy/filing → a personalized explainer that **can't over-claim** and proves what it showed | grounding is the trust unlock a pure generator structurally lacks |

Winning one funds the next on the same core, and the grounding advantage travels into the regulated markets that generative-video vendors cannot serve. *(Industry figures are order-of-magnitude framing.)*

---

## What we're building (the hackathon demo)

To prove the engine, we ship **one flawless live demo** rather than many half-demos:

- **Hero demo — one product ad** (a fictional EV scooter, *Vega V1*): paste the product page → grounded facts with spans → an interactive ad that swaps city/language/price live with **zero generation calls**, lets a viewer **ask** and get grounded answers or on-screen **refusals**, **embeds** into a third-party page in one line, and leaves a **signed receipt**.
- **Optional second ad product** (panels-only) — a brief live swap proving "same engine, different product." Built only after the hero is smooth; first to drop if time is short (decision **D13** in the plan).
- **Recorded 20-second proofs** — education, comic and news, showing one engine across sources without four live demos.

## The proof (what a judge can verify on screen)

- **Grounding coverage** — verified spans / claimed spans: **100%**.
- **Refusal correctness** — a 20-question set: **10/10 unsupported refused, 0 fabrications**.
- **Zero regeneration** — dozens of city × language variants rendered live, **network panel open, zero generation calls**.
- **Latency** — first frame < 2 s; nothing generative runs while a viewer watches.
- **Auditability** — a signed, chained play-log of exactly what each viewer saw.

Five reproducible numbers a reviewer could re-run — not five adjectives.

## Stack

- **Backend:** Python · FastAPI · LangGraph on Cloud Run
- **AI / media (build-time only):** Gemini (language) · Veo (motion) · Imagen / Gemini Image (stills) · Chirp TTS (voice) · Lyria (score) — all on Vertex AI, one service account, model-agnostic by design
- **Runtime:** React · TypeScript · Vite · Remotion Player (composition, gesture-scrubbed transitions)
- **Storage / infra:** Firestore · GCS · Cloud CDN · Firebase Hosting
- **The rule:** generation and encoding happen at build time; **play-time only composites** — the only live model calls are the two text calls the claim guard makes when a viewer asks.

## Repo layout

```
vachan-plan.md      # THE PLAN — full spec: ideation, features, demo script,
                    #   architecture, engineering, evals, delivery, pitch. Start here.
AGENTS.md           # Collaboration brief (model/tool-agnostic): what to build,
                    #   the rationale, working rules. Read before contributing.
PLAN_TRACKER.md     # Task log — one task at a time, updated as work is attempted.
VACHAN_VS_A2A.md    # How this build relates to the earlier, fuller design.
README.md           # This file.
docs_a2a/           # The earlier, fuller design docs (reference — see footnote).
backend/  frontend/ samples/   # code — created as the plan's phases (P0–P9) are built
```

## How to build

The plan is ordered by **demo value with a pre-committed cut line**, and structured for two builders in parallel against a manifest schema frozen early. Start at [`vachan-plan.md`](vachan-plan.md) §64 (build order), read [`AGENTS.md`](AGENTS.md) for the working rules, and log every task in [`PLAN_TRACKER.md`](PLAN_TRACKER.md) — **one task at a time, only after it is marked GO.**

---

<sub>

**† On A2A.** Vachan is the lean, ship-in-a-hackathon build of a broader vision codenamed **A2A** — the *same* grounded-knowledge engine, documented at full scope: four live verticals (Comic, Ads, Education, News), a typed-edge knowledge graph, and a temporal-validity layer. A2A is the multi-quarter *company* plan; Vachan is the *hackathon* plan that ships one flawless demo and pitches that vision as the roadmap — **build Vachan, pitch A2A.** The full A2A design lives in [`docs_a2a/`](docs_a2a/) (`PLAN.md`, `TECHNICAL_DESIGN.md`, `BUSINESS_CASE.md`, `VERTICALS.md`, `IMPLEMENTATION_PLAN.md`) and remains useful as deep reference — skip its typed edges, `valid_until`, and four-vertical config registry until after the demo. The name also matters: "A2A" collides with the agent-to-agent protocol, which is why the build carries the working name **Vachan**.

</sub>
