# AGENTS.md — Contributor & Agent Brief (Vachan)

A portable, tool- and model-agnostic orientation for anyone — human or AI agent — working in this repo. Read this before writing code or docs.

**Read order:** this file → [`vachan-plan.md`](vachan-plan.md) (the full plan) → [`PLAN_TRACKER.md`](PLAN_TRACKER.md) (what's been done / how work proceeds).

**Picking the build up mid-way?** Start with [`HANDOFF.md`](HANDOFF.md): current status, how to run it, and what remains.

---

## 1. What you're building

**Vachan** — grounded, interactive, personalized video. *Paste a source; get an interactive video that assembles itself for every viewer (language, city, price, and the questions they ask) and cannot say anything the source doesn't support.*

It is a **runtime, not a renderer**. The load-bearing split:
- **Generate (expensive, once, at build time):** a small library of persona-neutral media (stills/clips) → the **Vault**.
- **Compose (cheap, per viewer, at play time):** assemble the video in the browser (Remotion) — text, voice, language, price, branching — with **zero new generation**.

**The headline mechanism — the claim guard.** Every beat and answer is drawn from a flat fact carrying a *string-verified* source span; anything unsupported is **refused on screen**. The refusal is the thing a judge repeats in one sentence; grounding is the machinery that makes it possible.

**The three claims:** (1) generated once, composed per viewer; (2) true when you press play (live values resolve at play-time); (3) cannot over-claim, and proves what it showed (signed play-log).

## 2. Repo map

| Path | What |
|---|---|
| [`vachan-plan.md`](vachan-plan.md) | **THE plan** — ideation, features, demo script, architecture, engineering spec, evals, delivery, pitch. |
| [`PLAN_TRACKER.md`](PLAN_TRACKER.md) | The task log + the one-task-at-a-time workflow. |
| [`VACHAN_VS_A2A.md`](VACHAN_VS_A2A.md) | How Vachan relates to the older A2A plan. |
| [`README.md`](README.md) | Public-facing **pitch/marketing** — sells the full vision (industries, moat, roadmap). **Its scope is not the build scope** (see §4): we build Vachan only. |
| `docs_a2a/` | The older, fuller **A2A** design docs — reference & roadmap (see §3). |
| `backend/` `frontend/` `samples/` | Code — created as the plan's phases P0–P9 are built. |

## 3. History: A2A → Vachan

**A2A** is the broader vision this project grew from: a *grounded-knowledge engine that renders to interactive video* — the same generate-once/compose-per-viewer engine, but scoped to **four live verticals** (Comic, Ads, Education, News), a **typed-edge knowledge graph**, and a **temporal-validity layer** on facts. Its full design lives in `docs_a2a/` (`PLAN.md`, `TECHNICAL_DESIGN.md`, `BUSINESS_CASE.md`, `VERTICALS.md`, `IMPLEMENTATION_PLAN.md`) and remains useful as **deep reference**.

**Vachan is the same engine, scoped to ship.** ("A2A" also collides with the agent-to-agent protocol, hence the working name.)

## 4. Why Vachan, not A2A (the decision, and the reasoning behind it)

**A hackathon optimizes a different function than a product.** A product rewards breadth, generality, and multi-year defensibility; a hackathon rewards **one demo that works flawlessly in a few minutes, a mechanism a judge repeats in one sentence, and reproducible numbers on screen.** Against that function, A2A's superset (four live verticals, typed-edge Brain, temporal layer, ~40-ticket layered build) is cost with little on-stage payoff.

**The constraint is time, not money.**
- **A2A, as documented:** ~88 ideal person-days (~15–17 weeks solo); first demoable artifact deep into the schedule; four live verticals = four things to break on stage. Infeasible in a hackathon window.
- **Vachan:** ~25–30 ideal person-days (~3 weeks with two builders); the highest-value demo seconds work early; one live vertical, rehearsed.
- **Dollars are similar and small for both** — low hundreds of dollars, dominated by video-generation seconds × how often you regenerate, and almost certainly covered by free/sponsor cloud credits. Neither plan is dollar-expensive; play-time is near-free by design (`O(assets)`, not `O(viewers)`).

**Nothing load-bearing is lost.** Vachan preserves — and sharpens — every defensible property:
- refusal of unsupported claims → **the claim guard** (now the headline);
- a signed record of exactly what each viewer saw → **the play-log / receipt**;
- per-viewer composition at play-time and live values inside content → the two properties with **no comparable product**;
- "lives where customers are" → **the one-line embed**.
- What's dropped — **typed edges** and **fact-level temporal validity** — is deliberate (plan decision D11): no consumer ever traverses the graph, and freshness is delivered more simply by **bindings** (values resolved at play-time), never a wrong number.

**Demo portfolio (what actually goes on stage):**
- **One killer demo — a product ad** (the revenue angle). This is sacrosanct.
- **An optional second ad *product*** (panels-only, plan decision **D13**) — a brief live swap that doubles the revenue story and hedges "which renders smoothest," at ~zero engine cost because it reuses the runtime, guard and embed. Built only after the hero is smooth; first to drop if time is short.
- **Recorded 20-second proofs** (education, comic, news) carry the cross-industry generalizability claim. **Do not** build a second *live* vertical — that reopens the "four half-demos" trap (a new adapter, template set, interaction pattern, and rehearsal, and it blows the demo-time budget).

**The principle: build Vachan, pitch A2A.** The A2A docs in `docs_a2a/` are the roadmap and the Q&A depth behind the Vachan demo — not the build.

> **⚠️ `README.md` is the "pitch" half of that principle — do not mistake it for the build spec.** It deliberately markets the *full vision* (many industries, the moat, the roadmap) to sell the idea. Its breadth is **not** what we build. **What we build is the Vachan demo only:** the one hero ad (+ the optional second ad product, D13) and the recorded proofs, exactly as defined in `vachan-plan.md` and tracked in `PLAN_TRACKER.md`. If the README's scope ever seems to disagree with the plan, **the plan wins.**

**Cost hygiene:** run on free/sponsor credits; content-address every generated asset (reruns then cost nothing); cap generated transition clips at 4–6; never leave a video-generation regeneration loop running unattended (the one line item that can surprise you).

## 5. The plan in brief (so you can start without reading all of it)

- **Architecture:** `SOURCE → Brain → Bit Graph → Vault → Manifest → Runtime`, plus a **claim guard** on questions and a **play-log** on everything shown. (`vachan-plan.md` §23.)
- **The Brain is a fact store, not a graph DB:** three record types — entity, **fact** (the only unit the rest reads), span. `origin` ∈ `canon | inferred | imagined` decides what a fact may do. Facts are looked up by `subject` or `fact_id`; nothing traverses. (§24, D11.)
- **Facts vs bindings:** volatile values (price, stock, offer) are facts *and* play-time bindings, resolved by a fixed precedence ladder (live → cached → published fact → neutral wording), so a wrong number is never shown. (§24.2.)
- **Build order P0–P9**, ordered by demo value with a **pre-committed cut line** (§64–§65): P0 walking skeleton → P1 Brain + span verification → **P2 freeze the manifest schema** → P3 planner → P4 Vault → **P5 runtime + swap + embed** (the highest-value seconds) → P6 transition clips + gesture scrubbing → P7 claim guard → P7.5 play-log → P8 accessibility → P9 adapters/evals/deck/hardening.
- **Two builders in parallel** against the **manifest schema frozen at P2** — the only interface. **Backend never renders; runtime never generates.** (§66.)
- **Key decisions D1–D13** live in `vachan-plan.md` §3; note **D13** (optional second ad product) added per §4 above.
- **The pitch:** ~75 live demo seconds (§70), a slide-by-slide deck (§69), and **five reproducible metrics** (§60).

## 6. How work proceeds (non-negotiable)

Governed by [`PLAN_TRACKER.md`](PLAN_TRACKER.md):
1. **One task in flight at a time.**
2. **Work starts only after a task is marked `GO`** in the tracker — proposing is not permission.
3. **Log as you go**, especially shortcuts taken, things that couldn't be done, and **alternatives discovered during implementation** (a divergence from the plan is a decision — record it, and update the plan if warranted).
4. **Close before you open** — a task reaches `DONE`/`BLOCKED`/`DEFERRED` (with reason) before the next is proposed.

## 7. Engineering conventions (model/tool-agnostic)

- **The golden rule:** generation and encoding happen at **build time**; **play-time only composites.** The only live-path model calls are the two text calls the guard makes when a viewer asks a question — the viewer never waits on pixels.
- **No model is ever the guarantee.** Span verification is **mechanical** (normalized string match, not a model); the guard cannot assert a fact absent from its context. Every model output is checked by something that is not a model.
- **Content-address every generated asset** (`hash(model_version, prompt, seed, …)`) so reruns cost nothing and every asset is reproducible; make build steps **idempotent, content-hash-keyed**.
- **Models are swappable.** The build is Google-native by default (one service account: Gemini / Veo / Imagen·Gemini-Image / Chirp / Lyria), but the design is model-agnostic — any capable language/image/video/TTS model can slot in; pin exact versions in a `models.yaml` and print them in the build log.
- **The manifest schema is the contract.** Change it only with both builders' agreement (after P2).
- **No PII** in profiles or logs. **Kids mode** is a schema-level flag asserted by tests, not a runtime filter.
- **Protect the hero.** When time is short, cut from the bottom of the §65 cut line — never the mechanism beats (the swap, the refusal, the embed).

## 8. Quick start for a new contributor or agent

1. Read `vachan-plan.md` (at least §0, §6, §22–§32, §64–§66) and this file.
2. Open `PLAN_TRACKER.md`; if nothing is `GO`, **propose the next task** (start with **P0**, §64.2) and wait for go-ahead.
3. Build only the `GO` task; keep backend/runtime on their own side of the frozen manifest.
4. Record the outcome — including shortcuts and any divergence from the plan — in the tracker before moving on.
