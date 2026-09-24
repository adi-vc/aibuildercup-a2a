# A2A — Implementation Plan (Build Sequence)

> **Purpose.** This is the starter guide for implementation. If you are a fresh session picking up this project, **read this file first**, then build the tickets **in the phase order of §2** (top to bottom — *not* by numeric ID: the fractional tickets T28.5/T29.5/T30.5 are built **last**, in Phase 7.5, after T30). Each ticket is a self-contained unit that stands on top of the ones before it; completing them in order produces the entire system. Every ticket cites the exact section(s) of [`TECHNICAL_DESIGN.md`](./TECHNICAL_DESIGN.md) it implements — that doc is the source of truth for *how* each piece behaves; this doc is the ordered list of *what* to build and *when*.

---

## 0. Read first (context)

| Doc | What it gives you |
|---|---|
| [`PLAN.md`](./PLAN.md) | The idea, MVP scope, pipeline, repo layout. Start here for the 5-minute mental model. |
| [`TECHNICAL_DESIGN.md`](./TECHNICAL_DESIGN.md) | **The spec.** Data model, agents, LangGraph orchestration, generation/composition split, `when` grammar, manifest pruning, storage, consistency, deployment, the §10.1 Google service map. Every ticket references it. |
| [`VERTICALS.md`](./VERTICALS.md) | The four verticals / five demos (Comic 0, Ads A/B, Education C, News D) as configs of the same engine; per-vertical worked examples + economics. |
| [`BUSINESS_CASE.md`](./BUSINESS_CASE.md) | Why it matters; the narrative-only future verticals. Not needed to build, useful for framing. |
| `~/.claude/plans/side-project-…federated-stallman.md` | The original pre-refinement plan snapshot (historical). |

**One-paragraph recap.** A2A turns any source into an *interactive* video: an agentic pipeline builds a grounded knowledge graph (**Brain**), plans an interactive video graph (**Bit Graph**), and generates a persona-neutral media **Vault** — **Gemini-image panels by default** (`media_mode: panels`), Veo clips for high-end. A **Remotion** client runtime composes/personalizes per an editable `profile.json` — **generate once, re-render per viewer** — and viewers can **ask characters** grounded questions (claim-guarded). Four verticals ship as configs: **Comic** (`branch_explore` + ask-a-character), Ads (`feature_router`), Education (`branch_explore` + character consistency), News (`hub_spoke` + procedural deepening + scheduler). Orchestrated by **LangGraph**; Google-native stack (see §10.1 service map).

---

## 1. Environment & conventions

**Stack (per §10 / §10.1):** Python + FastAPI on Cloud Run; LangGraph orchestration; Gemini/Veo/Imagen on Vertex AI (`google-genai`); Cloud Text-to-Speech (Chirp); Firestore + GCS; React + TS + Vite + Remotion frontend on Firebase Hosting.

**Before T00 you need:** a GCP project with **Vertex AI (Gemini + Veo + Imagen)**, Firestore, GCS, Cloud TTS, Cloud Tasks, Cloud Scheduler enabled (plus **Document AI + Cloud Vision** before the Education phase, T21); a service account; and confirmed **Veo access/quota + region** (Open-Q #1). **Veo gates only the `cinematic` paths** — the car variant (T20), the `cinematic` sub-mode of T11/T22, and lazy-Veo (T27/T28/T28.5); the **`panels` default (Gemini-image) needs no Veo**, so T11 and every panels vertical proceed without it. Resolve Open-Q #3 (source fetching behind proxy) before T04. **Enabling an API ≠ creating the resource — T00.5 provisions the actual Firestore DB, buckets, Tasks queue, and IAM.**

**Conventions (apply to every ticket):**
- Invoke Python as **`python`** (not `python3`) per machine setup.
- **Contract-first:** T01 pydantic models are the shared contract; nothing bypasses them.
- **Config, not branches (§2.2):** vertical differences live in `vertical.config.json`, never in `if vertical == …` code.
- **Definition of done** for each ticket = code + unit tests + a runnable check (script or endpoint) that demonstrates the acceptance criterion. Keep each ticket independently verifiable.
- **Grounding is non-negotiable (§1.2):** never emit output that doesn't trace to a Brain node → source span.
- **Cost thesis (§1.1):** personalization is composition-time; never trigger media generation (a panel/clip) to personalize.

**Target repo layout (create in T00, fill as you go):**
```
backend/app/
  main.py                     # FastAPI app + routers            (T02→, T12)
  models.py                   # ALL pydantic schemas             (T01)
  clients.py                  # Vertex/GCS/Firestore/TTS clients   (T00)
  config/vertical_config.py + verticals/{comic,ads,education,news}.json (T03)
  storage/{firestore,gcs,signed_urls}.py                         (T02)
  graph/{brain,bitgraph}.py                                      (T01/T08/T10)
  expr/when.py                # sandboxed when-expr parser/interp (T05)
  binding/{scope,localize,cache}.py                              (T06)
  orchestration/{pipeline,invalidation}.py  # LangGraph          (T07, T32)
  agents/ingest.py, enrich.py, planner.py                        (T08,T09,T10)
  agents/adapters/{web_url,pdf,comic,news_feed}.py               (T04,T21,T25)
  agents/patterns/{feature_router,branch_explore,hub_spoke}.py   (T10,T23,T26)
  vault/builder.py, panels.py, veo.py, imagen.py, tasks.py, procedural.py (T11,T27,T28)
  vault/consistency/{product_anchor,character_sheets,generic_broll}.py (T11,T22)
  session/{api,manifest,vo}.py                                   (T12,T13)
  scheduler/bulletin_job.py                                      (T29)
  observability/logging.py                                       (T31)
frontend/src/
  api/client.ts                                                  (T14)
  compositions/*.tsx          # per-vertical template sets       (T15,T23,T26.5,T29.5)
  personalize/bindProps.ts                                       (T16)
  player/InteractivePlayer.tsx                                   (T16)
  profile/ProfilePanel.tsx, grounding/GroundingPanel.tsx         (T16,T17)
  studio/Studio.tsx, audio/AudioOnlyComposition.tsx, ask/AskBox.tsx (T18,T19,T28.5)
samples/                       # sample sources + fixtures + Veo-less seed project (T04→, T13.5)
infra/                         # GCP provisioning + deploy skeleton (Terraform/gcloud) (T00.5)
```

---

## 2. Build sequence at a glance

Sequential; later tickets assume earlier ones. **Four demo milestones** gate the phases (Comic is "Demo 0" — the flagship — but is built last because it reuses the most machinery).

```
Phase 0  Foundations         T00 T00.5 T01 T02 T03
Phase 1  Core primitives     T04 T05 T06
Phase 2  Agent pipeline      T07 T08 T09 T10 T11
Phase 3  Session/runtime     T12 T13 T13.5
Phase 4  Frontend runtime    T14 T15 T16 T17 T18 T19
Phase 5  ▣ MILESTONE 1 — ADS demo end-to-end            T20
Phase 6  Education vertical  T21 T22 T23 → ▣ MILESTONE 2 — T24
Phase 7  News vertical       T25 T26 T26.5 T27 T28 T29 → ▣ MILESTONE 3 — T30
Phase 7.5 Ask + Comic        T28.5 (ask-a-character) · T29.5 (comic templates) → ▣ MILESTONE 0 (flagship) — T30.5
Phase 8  Hardening           T31 T32
```
**Inserted after the review (fractional IDs keep every existing `Depends on T##` reference valid):** **T00.5** provisions GCP resources + deploy skeleton; **T13.5** a Veo-less seed sample project so the frontend (T14–T18) is verifiable *before* the Ads Vault build and independent of Veo access; **T26.5** the News composition templates. T19 (audio-only) lives in Phase 4 and is consumed at Milestone 3 (News); T20 does not depend on it.

**Added for StoryGraph parity:** **T28.5** ask-a-character (grounded Q&A + claim guard) and **T29.5/T30.5** the Comic vertical (templates + flagship demo) reuse Education's `character_sheets` + News's procedural/lazy vault, so they build last. Three **cross-cutting** additions — **`media_mode`** (`panels` default vs `cinematic`/Veo), **`veracity`** (canon/imagined), and **`valid_until`** (fact expiry) — are folded into existing tickets (T01/T08/T10/T11/T15/T17/T32), not new phases.

### Effort & critical path (rough)

Order-of-magnitude estimates in **ideal engineer-days** (S≈1, M≈2, L≈3–4). Treat as relative sizing, not commitments — the LLM/Veo integration tickets carry the most uncertainty (flagged ⚠). "∥" = parallelizable with siblings in its phase.

| Phase | Tickets (size · days) | Subtotal |
|---|---|---|
| 0 Foundations | T00 M·2 · T00.5 S·1 · T01 M·2 · T02 M·2 · T03 S·1 | ~8 |
| 1 Core primitives | T04 M·2 · T05 M·2 (∥ T04) · T06 L·3 | ~7 |
| 2 Agent pipeline | T07 L·4 ⚠(custom checkpointer) · T08 L·3 ⚠ · T09 M·2 · T10 L·3 ⚠ · T11 L·3 ⚠(Veo/Imagen) | ~15 |
| 3 Session/runtime | T12 L·4 (manifest logic) · T13 M·2 · T13.5 S·1 | ~7 |
| 4 Frontend | T14 M·2 · T15 L·3 · T16 L·3 · T17 S·1 (∥) · T18 M·2 (∥) · T19 S·1 (∥) | ~12 |
| 5 ▣ M1 Ads | T20 M·2 | ~2 |
| 6 Education | T21 M·2 · T22 L·3 ⚠(character consistency) · T23 M·2 · T24 M·2 | ~9 |
| 7 News | T25 M·2 · T26 M·2 · T26.5 M·2 · T27 L·3 · T28 L·3 ⚠(procedural loop) · T29 S·1 · T30 M·2 | ~15 |
| 7.5 Ask + Comic (flagship) | T28.5 M·2 (ask-a-character) · T29.5 M·2 (comic templates) · T30.5 M·2 | ~6 |
| 8 Hardening | T31 M·2 · T32 M·2 | ~4 |
| cross-cutting | `media_mode` / `veracity` / `valid_until` folded into T01,T08,T10,T11,T15,T17,T32 | ~3 |
| **Total** | | **~88** |

**Milestones (cumulative ideal-days):** M1 Ads = **~51** (Phases 0–5) · M2 Education = **+9** · M3 News = **+15** · M0 Comic (flagship) = **+6** · hardening **+4** · cross-cutting **+3**.

**Critical path & parallelism:**
- The backbone is serial: `T00→T00.5→T01→T02→T06→T07→T08→T09→T10→T11→T12→T13.5→(frontend T14→T15→T16)→T20`. T04∥T05, and T17/T18/T19 run in parallel within Phase 4.
- **Two-track split** once T12+T13.5 exist: a backend dev finishes the pipeline while a frontend dev builds T14–T19 against the **Veo-less seed (T13.5)** — this is the main reason T13.5 was added.
- **After M1, Education (T21–T24) and News (T25–T30) are independent tracks** — parallelize across devs.
- Wall-clock: **solo ≈ 15–17 weeks**; a **backend+frontend pair with vertical parallelism ≈ 6–8 weeks**.
- **Highest-risk tickets (pad these):** T07 (custom Firestore LangGraph checkpointer), T11/T22 (panel/character consistency; the `cinematic`/Veo sub-mode is gated by Open-Q #1), T28 (bounded procedural loop + caching).
- **Hackathon-week cut:** a compelling *Ads-only* demo needs just T00,T01,T03(ads),T05,T06(no translate),T12(route path only),T13.5,T14,T15,T16 with a **pre-canned Brain + brand-card/still fallbacks (no live Veo)** — roughly **~2 weeks**. Everything else is the path to the full product.

---

## 3. Tickets

Format — **ID · Title** `[vertical]` · **§refs** · **Depends on** · **Build** · **Done when**.

### Phase 0 — Foundations

#### T00 · Project scaffolding & GCP clients `[all]`
- **§refs:** §2, §10, §10.1 · **Depends on:** —
- **Build:** monorepo (`backend/`, `frontend/`, `samples/`, `infra/`) with **dependency manifests** (`pyproject.toml`/`requirements.txt` pinning `langgraph`, `google-genai`, `fastapi`; `package.json` pinning `react`, `vite`, `remotion`); FastAPI skeleton (`main.py` health route) **with CORS middleware** (allow the frontend origin); Vite+React+TS skeleton; a `backend/app/clients.py` initializing Vertex AI (`google-genai`), GCS, Firestore, Cloud TTS clients from a service account; `.env`/Secret Manager config loader; a **test harness** (pytest + vitest, with a fixtures dir); Dockerfile for Cloud Run; local run scripts (backend + frontend together).
- **Done when:** `GET /health` returns 200 locally; a smoke script calls Gemini on Vertex AI and gets a completion; GCS/Firestore clients authenticate; a CORS preflight from the frontend origin succeeds; `pytest`/`vitest` run green on a trivial test.

#### T00.5 · Provision GCP resources & deploy skeleton `[all]`
- **§refs:** §7, §10, §10.1 · **Depends on:** T00
- **Build:** an infra script (`infra/`, Terraform or `gcloud`) that **creates the actual resources** (enabling an API is not creating it): the **Firestore database** (native mode + region), the `a2a-vault` **GCS bucket(s) with CORS** (so the browser / `@remotion/player` can fetch signed URLs), a **Cloud Tasks queue** (for T27's background gen), and the service-account grants — `roles/iam.serviceAccountTokenCreator` (V4 signed-URL `signBlob`) plus Firestore/GCS/Vertex/TTS roles. Also lay the **deploy skeleton**: Cloud Run service config + `firebase.json`/`.firebaserc` for Hosting, so the first real deploy (T20) is content-only, not first-time setup. (Cloud Scheduler job is created in T29; Document AI/Vision enabled before T21.)
- **Done when:** Firestore reads/writes succeed; a file uploads to the bucket and a **V4 signed URL streams in a browser** (CORS + `signBlob` working); the Tasks queue exists; a placeholder `gcloud run deploy` and `firebase deploy` succeed.

#### T01 · Data-model schemas (the shared contract) `[all]`
- **§refs:** §3.1 (Brain node/edge, `Set` node, span + image-anchor provenance), §3.2 (Bit, edge with `mode`, `media.request`/`media.vault`, slots), §3.3 (Vault entry), §3.4 (`profile.json`), §2.2 (`vertical.config.json`) · **Depends on:** T00
- **Build:** `models.py` with pydantic models for: `Source` (+ `normalized`, `normalizer_version`), `BrainNode`/`Edge`/`Provenance` (span **and** image-anchor variants; provenance `valid_from`/`valid_until`; node/bit `veracity: canon|imagined`) incl. `Set`; `BitGraph`/`Bit`/`Edge` (`default_next`|`user_choice`|`personalization_conditional` with optional `mode: route|include`); `MediaRequest`/`MediaRef`/`VaultEntry` (kind `panel_still|veo_clip|imagen_still|brand_card`); `Profile` (open dict + typed helpers); `VerticalConfig` (all §2.2–§2.3 fields incl. `graph_policy.interaction.{max_depth,ask_character}` and `vault_policy.{media_mode,generation:list}`).
- **Done when:** models round-trip the exact JSON examples in §3.1/§3.2/§3.3/§4.4 **and the four §2.3 configs**; `veracity` defaults to `canon`, `media_mode` to `panels`; invalid edges (e.g. `mode` on a non-conditional) are rejected by validation.

#### T02 · Storage layer `[all]`
- **§refs:** §7, §6 (signed URLs) · **Depends on:** T01
- **Build:** `storage/firestore.py` (CRUD for Brain, Bit Graph, sessions — doc-per-project), `storage/gcs.py` (put/get Vault media + VO cache with the `(bit,lang,text_hash)` keying), `storage/signed_urls.py` (V4 signed GET URLs). Repository interfaces so callers never touch SDKs directly.
- **Done when:** a Brain + Bit Graph persist and reload byte-identical; a file uploads to GCS and a signed URL streams it.

#### T03 · Vertical-config registry + the four configs `[all]`
- **§refs:** §2.2 (full config table + "who reads what"), §2.3 (fixtures) · **Depends on:** T01
- **Build:** `config/vertical_config.py` (load + validate a `VerticalConfig`, expose typed accessors); the four fixtures `verticals/comic.json`, `ads.json`, `education.json`, `news.json` — **lift them verbatim from the concrete configs in TECHNICAL_DESIGN §2.3** (strip `//` comments; omit roadmap fields). A `get_config(id)` used everywhere downstream.
- **Done when:** all four configs load and validate; a unit test asserts each field matches TECHNICAL_DESIGN §2.2/§2.3.

### Phase 1 — Core primitives

#### T04 · Source normalization + `web_url` adapter `[all; web_url]`
- **§refs:** §3.1 (canonical versioned `normalize`), §4.1 (adapters) · **Depends on:** T01, T02
- **Build:** `normalize(source)` v1 (HTML→text, NFC, whitespace collapse — deterministic), persist `normalized` + `normalizer_version` on the `Source`; `agents/adapters/web_url.py` (Cloud Run fetch of a URL + images). Add 2–3 sample product pages to `samples/`.
- **Done when:** normalizing a fixture is deterministic and idempotent; offsets into `normalized` are stable; a sample URL yields normalized text + image list.

#### T05 · `when` expression language (sandboxed) `[all]`
- **§refs:** §3.2.2 (EBNF, sandbox rules), §3.1 (`Set` resolution) · **Depends on:** T01
- **Build:** `expr/when.py` — hand-written recursive-descent **parser** + tree **interpreter** for the EBNF; **no `eval`**; only `profile.*` readable; `SET_IDENT` resolves to a `Set` node's `members`; total + side-effect-free (any error → `false`); type-checked comparisons; `in` membership.
- **Done when:** unit tests cover every §3.2.2 example plus adversarial inputs (unknown identifier → parse error/false; missing field → no match; injection-y strings never execute).

#### T06 · Slot binding → localize → cache `[all]`
- **§refs:** §3.2 (bind scope, first-of-type resolution, translatable-field rules, cache keys) · **Depends on:** T01, T02, T00 (Gemini)
- **Build:** `binding/scope.py` (assemble bind scope from a bit's grounded nodes + profile; profile-derived roots `language`/`lens`/`interests`; **first-of-type** resolution + plan-time duplicate warning; hard bind-error on unresolved path); `binding/localize.py` (Gemini translate for translatable fields when `profile.language` ≠ source; numeric `stat.value` kept, unit/suffix translated + locale-formatted; **plus a reading-level rewrite keyed on `profile.grade`/`difficulty`/`age_level`** — simpler/harder copy for Education *and* Comic, §3.2); `binding/cache.py` (key `(node_id|profile_path, field, source_text_hash, target_lang, reading_level)`). (VO/TTS is T13.)
- **Done when:** on a fixture bit+brain, binding resolves all slots; a non-source language triggers cached Gemini translation; duplicate-type grounding emits the warning.

### Phase 2 — Agent pipeline (LangGraph)

#### T07 · LangGraph pipeline skeleton + checkpoints + invalidation `[all]`
- **§refs:** §2.1 (state machine, checkpointer, `interrupt` gates, dependency-diff invalidation) · **Depends on:** T01, T02, T03
- **Build:** `orchestration/pipeline.py` — LangGraph graph `INGESTED→ENRICHED→PLANNED→VAULT_READY→LIVE` with **`interrupt`** at each gate honoring `hitl.gates` (`review|auto|approve`); agent nodes wired as **stubs first, replaced by the real agents as T08–T11 land**. **Checkpointer:** `langgraph-checkpoint` ships Postgres/SQLite/Redis/Mongo — *not* Firestore — so implement a **custom Firestore `BaseCheckpointSaver`** (preferred; keeps one store) *or* use **Cloud SQL Postgres** with the official saver. **Pipeline HTTP layer:** expose the §6 pipeline verbs — `POST /ingest`, `/enrich`, `/plan`, `/vault/build`, `/projects/:id/approve` — mapping onto LangGraph run/`interrupt`/resume (this is how Studio T18 and the demo T20 drive the gates). `orchestration/invalidation.py` — dependency-diff: each artifact records input keys; editing recomputes only changed downstream, marks vault entries `stale` but retained (never blanket-regenerate).
- **Done when:** the pipeline endpoints drive a run through its gates over HTTP; a run pauses at a `review` gate and resumes on approve; an `auto` gate passes through; editing a Brain node invalidates only dependent bits/vault entries (asserted by a diff test).

#### T08 · Ingest agent `[all; extends per adapter later]`
- **§refs:** §4.1 (extract + verify/repair loop), §3.1 (provenance, image-anchor) · **Depends on:** T04, T05, T07
- **Build:** `agents/ingest.py` — **reads `brain_schema.node_types` from `get_config(id)`** into the extraction prompt (no hardcoded per-vertical types); accepts optional `guidance`; Gemini **structured output** → Brain nodes/edges with `provenance` (incl. `valid_from`/`valid_until` where the source states a time window, e.g. "valid till Sunday"); all grounded nodes are `veracity: canon`; the **verify+repair loop** (exact → unique-relocate → drop, report drops at checkpoint); image-anchored nodes validated against supplied images; emit `Set` nodes where the source implies lookup lists.
- **Done when:** on a sample product page, every accepted node's `text` slice matches `normalized[span]`; hallucinated spans are dropped and reported.

#### T09 · Enrich agent `[all]`
- **§refs:** §4.2 · **Depends on:** T08
- **Build:** `agents/enrich.py` — derive second-order nodes per `brain_schema.node_types` (benefits/personas, causal links, topic clusters), a **style/skin**, and **character/spokesperson sheets** (look descriptor + assigned TTS voice/lang); accepts optional `guidance` to bias the derivation; mark `inferred`.
- **Done when:** Ads Brain gains benefits + personas + brand skin; inferred nodes flagged; runs behind its gate.

#### T10 · Planner agent + pattern strategies `[all; feature_router first]`
- **§refs:** §4.3, §4.3.1 (topology + edge-mix + prompt skeletons), §3.2 · **Depends on:** T03, T09
- **Build:** `agents/planner.py` (emit Bit Graph; each bit ≥1 grounding; `veracity: canon` by default, what-if/hypothetical bits marked `imagined`; media as **`media.request`**, never a clip_id; accepts optional `guidance`); `agents/patterns/feature_router.py` (prompt skeleton + required-topology validator: hook→router→features→CTA, router has `default_next` fallback). Backend rejects/re-prompts on topology violation. (branch_explore=T23, hub_spoke=T26.)
- **Done when:** Ads planner produces a valid `feature_router` Bit Graph with route-mode conditionals over `conditional_over`, every bit grounded, media as requests; validator catches a missing fallback.

#### T11 · Vault builder (prebuild_all) + `media_mode` + product_anchor + fallback `[all; ads]`
- **§refs:** §4.4 (dedupe key, `media_mode`, patch `media.vault`, fallback chain, `prebuild_all`), §8.1 (`product_anchor`) · **Depends on:** T02, T10, T00 (Gemini-image/Imagen/Veo)
- **Build:** `vault/panels.py` (**Gemini image / Imagen** — the `panels` **default**, kind `panel_still`) + `vault/veo.py` (the `cinematic` mode, kind `veo_clip`) + `vault/imagen.py`; `vault/builder.py` — **branch on `vault_policy.media_mode`** to pick the generator; resolve each `media.request` via **dedupe key** `sha256(normalize_prompt)+":"+sorted(depicts)`; the dedupe lookup **honors `cache_scope`** (`per_source` key prefix vs `shared_global`); generate if absent, store to GCS, patch `media.vault`; **fallback chain** generator→Imagen still→brand-card; honor an operator-chosen **`features` subset + `seed_images`** (from `/vault/build`); `vault/consistency/product_anchor.py` (Imagen neutral still + fixed seed, template-stable prompts). Enforce the **neutrality contract** (no text/logos baked) in prompts.
- **Done when:** the Ads vault builds behind its gate in **`panels`** by default (Gemini-image `panel_still`s) and in `cinematic` when switched (Veo); identical requests dedupe to one entry; generation prompts carry the no-text/no-logo **neutrality constraint** (§3.3); a forced generation failure resolves to a still/brand-card, never a broken ref.

### Phase 3 — Session / runtime backend

#### T12 · Session API + manifest pruning + splice-forward `[all]`
- **§refs:** §6, §6.1 (route + include pruning & re-stitch), §6.2 (splice-forward), §6.3 (loading/error) · **Depends on:** T05, T06, T11
- **Build:** `session/api.py` (the §6 **runtime** endpoints `/session`, `/session/:id/bit`, `/advance`, `/session/:id/profile`, `/grounding`, **plus the operator-edit routes `PATCH /projects/:id/brain` and `PATCH /projects/:id/bitgraph`**; the pipeline verbs `/ingest|/enrich|/plan|/vault/build|/approve` live in T07); `session/manifest.py` — build the profile-resolved manifest: **route** path (first-match, drop others) and **include** path (independent keep/prune + `default_next` re-stitch per the §6.1 algorithm — built here, its News re-stitch is exercised/tested at T26); `user_choice` always kept; annotate `auto`/`choice`; **splice-forward** on profile edit (re-resolve from nearest affected router, no restart); loading/error placeholder states.
- **Done when:** for an Ads project, switching `profile` re-routes the manifest live; a mid-session edit splices forward without restart; grounding endpoint returns node + source span. (Include-mode fully exercised at Milestone 3, but implement both paths now.)

#### T13 · Localized VO (Cloud TTS) `[all]`
- **§refs:** §5.3, §3.2 (VO cache key) · **Depends on:** T02, T06, T09 (assigned voice), T12 (session resolve)
- **Build:** `session/vo.py` — render VO per bit with **Cloud Text-to-Speech (Chirp)** using the assigned voice for `profile.language`; derive captions from TTS timepoints; cache by `(bit_id, language, text_hash)` in GCS; wired into session resolve.
- **Done when:** session resolve returns a signed VO URL + timed captions; a repeat request is a cache hit.

#### T13.5 · Seed sample project (Veo-less) `[all]`
- **§refs:** §3.1/§3.2 (fixtures), §4.4 (fallback chain) · **Depends on:** T12
- **Build:** a hand-authored sample project checked into `samples/` — a small Brain + a `feature_router` Bit Graph + a resolvable session **whose media resolves to Imagen-still / brand-card fallbacks** (no Veo needed). Serve it via the Session API so the frontend (T14–T18) has a real manifest to render **before** the Ads Vault build (T20) and **independent of Veo access** (Open-Q #1).
- **Done when:** `POST /session` on the seed project returns a full manifest the frontend can play end-to-end using only fallback media.

### Phase 4 — Frontend runtime (Remotion)

#### T14 · Frontend scaffold + Remotion + API client `[all]`
- **§refs:** §5, §10 (Firebase Hosting) · **Depends on:** T13.5
- **Build:** Remotion + `@remotion/player` integrated into the Vite app; `api/client.ts` typed via **generated types** (FastAPI OpenAPI → TS with `openapi-typescript`) so the manifest/bound-bit shapes derive from the T01 pydantic models and can't drift; a dev harness page that loads the **T13.5 seed** session manifest.
- **Done when:** the player renders the seed manifest (T13.5) end-to-end from fetched data (fallback media only, no Veo needed).

#### T15 · Ads composition templates + brand-card `[ads]`
- **§refs:** §5.2 (layering, per-vertical `template_set`), §4.4 (brand_card kind) · **Depends on:** T14
- **Build:** `compositions/{Hook,Feature,Benefit,CityOffer,CTA,BrandCard}.tsx` — typed props; layering `media → brand skin → headline/stat → captions → VO → transitions`; a shared **media layer handling every `media.kind`** — **`panel_still` (default): animate on-device** (Ken-Burns pan/zoom, bubble pop-in, transitions, §5.6); `veo_clip`: play; `imagen_still`/`brand_card`: fallbacks; `BrandCard` renders from brand theme + headline. **Text/captions are composed, never baked** (§3.3).
- **Done when:** each template renders from typed props with an animated `panel_still` (default), a `veo_clip`, a still, and a brand-card fallback.

#### T16 · Personalize layer + InteractivePlayer + ProfilePanel `[all]`
- **§refs:** §5.4 (traverse **server-resolved manifest**, prefetch), §5.1, §6.2 · **Depends on:** T15
- **Build:** `personalize/bindProps.ts` (manifest bound-bit → template props); `player/InteractivePlayer.tsx` (state machine over the manifest — **never** evaluates raw `when`; follows annotated edges; renders `user_choice` buttons; prefetches successors' media+VO); `profile/ProfilePanel.tsx` (**enumerates & validates the editable fields from `vertical.config.profile_schema`**; edit `profile.json` → `POST /session/:id/profile` → live splice-forward re-render).
- **Done when:** editing the profile panel visibly re-routes the playing video (the "watch it re-render" moment); branches play instantly via prefetch.

#### T17 · GroundingPanel `[all]`
- **§refs:** §6 (`/grounding`), §1.2 · **Depends on:** T16
- **Build:** `grounding/GroundingPanel.tsx` — hover/select a bit → show its grounded nodes → source span/text (or image-anchor bbox); render an **"imagined" badge** for `veracity: imagined` bits and a **"true until …" badge** for facts carrying `valid_until` (§3.1).
- **Done when:** every playing bit reveals the exact source span it traces to; inferred nodes are marked; imagined bits show the imagined badge; expiring facts show "true until …".

#### T18 · Studio (HITL checkpoint UI) `[all]`
- **§refs:** §2.1, Open-Q #4 (MVP fidelity = JSON edit + guidance + approve) · **Depends on:** T16, T07
- **Build:** `studio/Studio.tsx` — per-stage review surface hitting the `PATCH`/`POST /approve` endpoints: view the draft (Brain / Bit Graph / Vault), JSON-level edit, add `guidance` + seed images, re-run, approve to advance. Show dropped-node reports (T08) and duplicate-type warnings (T06).
- **Done when:** an operator can walk Ads from ingest→LIVE through the gates, editing at least one artifact and re-running.

#### T19 · Audio-only compositor path `[news; shared runtime]`
- **§refs:** §5.5 · **Depends on:** T16
- **Build:** `audio/AudioOnlyComposition.tsx` — when `profile.format == "audio"`, skip video: VO track + timed captions over a static brand/still card; **bit duration = TTS length**; interaction layer unchanged. (Build here so the runtime supports it; exercised at Milestone 3.)
- **Done when:** toggling `format: audio` plays VO+captions over a card with correct durations and working branch buttons.

### Phase 5 — ▣ Milestone 1: Ads demo end-to-end

#### T20 · Wire & ship the Ads demo (car + earbuds) `[ads]`
- **§refs:** VERTICALS §4; §2.2 Ads config; §9 (cold/warm path) · **Depends on:** T11, T13, T16–T18
- **Build:** run the full pipeline on the car and earbuds sources; pre-generate both Vaults (`prebuild_all`) — the **car** in `cinematic` (Veo, showcasing the filmic path) and **earbuds** in `panels` (default), so one vertical demonstrates both render modes; author/verify the `feature_router` graphs; deploy backend to **Cloud Run** and frontend to **Firebase Hosting**; a demo script that changes `profile.json` (location/household/intent/language) and shows live re-render + drill-down + grounding.
- **Done when:** paste-source → step gates → interactive personalized ad; switching profile re-renders on the fly with **zero new generation**; provenance visible per bit. **This is the first shippable demo.**

### Phase 6 — Education vertical

#### T21 · Education adapters (Document AI / comic) `[education]`
- **§refs:** §4.1 (adapters), §3.1 (image-anchor) · **Depends on:** T08
- **Build:** `agents/adapters/pdf.py` (**Document AI** layout+OCR for textbook chapters → normalized text + page images) and `agents/adapters/comic.py` (**Gemini** multimodal + **Cloud Vision** OCR). Feed the same ingest/verify path; image-anchored nodes for panels/figures. Place a **sample history chapter (PDF) + a sample comic** in `samples/`; support a paste/upload fallback (Open-Q #3).
- **Done when:** a sample history chapter ingests into a grounded Brain (characters/events/places), spans/anchors verified.

#### T22 · `character_sheets` consistency `[education]`
- **§refs:** §8.2 · **Depends on:** T11, T09
- **Build:** enrich produces per-character sheets `{reference_still (Imagen, once), fixed seed, look phrase}`; `vault/consistency/character_sheets.py` — each depicting panel/clip is generated **image-conditioned on `reference_still`** + seed + look phrase; **with `media_mode: panels` (default) that's a Gemini-image `panel_still`; `cinematic` uses Veo** — identical anchoring; **multi-character** = pass all present stills + concatenated look phrases + spatial cues + deterministic ensemble seed.
- **Done when:** the same character renders recognizably across multiple generated clips; a two-character scene reproduces deterministically.

#### T23 · `branch_explore` templates + planner strategy `[education]`
- **§refs:** §4.3.1 (branch_explore topology, user_choice-only), §5.2 (Education `template_set`) · **Depends on:** T10, T15
- **Build:** `agents/patterns/branch_explore.py` (arc-intro → K `user_choice` topic bits → deeper `user_choice` sub-bits; **no** conditional routing — `grade` affects binding, not routing); `compositions/{SceneNarration,CharacterBeat,EventCard}.tsx`.
- **Done when:** an Education Bit Graph offers `user_choice` exploration; validator enforces the topology; templates render.

#### T24 · ▣ Milestone 2: Education demo end-to-end `[education]`
- **§refs:** VERTICALS §5; §2.2 Education config · **Depends on:** T21–T23, T20 infra
- **Build:** run pipeline on a Modern-Indian-History chapter; `prebuild_all` character-consistent Vault; teacher-accuracy checkpoint (grounding-assisted); demo the game-like branch exploration; multiple learners take different routes over one Vault.
- **Done when:** a student steers a grounded, branching history "movie"; different routes re-render with no regeneration; scenes trace to textbook lines. **Second shippable demo.**

### Phase 7 — News vertical

#### T25 · `news_feed` adapter + persistent incremental Brain `[news]`
- **§refs:** §4.1, §4.5 (key-based upsert), §2.2 (`persistent_incremental`) · **Depends on:** T08
- **Build:** `agents/adapters/news_feed.py` (fetch day's articles; place **sample feed articles** in `samples/` with a paste/upload fallback, Open-Q #3); incremental merge = **key-based upsert** `(normalized(label), type)` → update attrs + append provenance, else insert. (Full entity resolution = roadmap.)
- **Done when:** two days' feeds merge so shared entities accrue provenance without duplication; only net-new events add nodes.

#### T26 · `hub_spoke` planner + include-mode manifest `[news]`
- **§refs:** §4.3.1 (hub_spoke), §3.2.1 (include mode), §6.1 (include pruning + re-stitch) · **Depends on:** T10, T12
- **Build:** `agents/patterns/hub_spoke.py` (hub + K candidate items; each gated by a `personalization_conditional` **`mode:"include"`** edge on `profile.interests`; **cap surviving items by `profile.length_min`** — MVP; `default_depth` = roadmap; fixed plan-time order; per-item `user_choice` deep-dive stubs). Verify T12's include path re-stitches survivors correctly (hub→first→…→recap).
- **Done when:** interests=[finance,cricket,geopolitics] yields all three items in fixed order; interests=[cricket] yields one item + recap; order identical across viewers; a **mid-session `interests` edit** re-stitches survivors from the hub without replaying seen items (§6.1/§6.2).

#### T26.5 · News composition templates `[news]`
- **§refs:** §5.2 (News `template_set`), §4.4 (media kinds) · **Depends on:** T14, T26
- **Build:** `compositions/{NewsItem,DeepDive,Recap}.tsx` — typed props, same layering as T15 (`media → skin → headline/stat → captions → VO → transitions`); handle `veo_clip | imagen_still | brand_card`; `DeepDive` renders a procedurally-generated deep-dive bit; `Recap` closes the bulletin. (Mirrors T15/T23 for the News set, which was otherwise unbuilt — the review's one Blocker.)
- **Done when:** each News template renders from typed props with a vault clip, an Imagen still, and a brand-card fallback; the audio-only (T19) variant renders over a card.

#### T27 · `reuse_global` + `lazy_on_demand` vault (Cloud Tasks + single-flight) `[news]`
- **§refs:** §4.4 (reuse_global, lazy_on_demand), §8.3 (`generic_broll`), §10 (Cloud Tasks) · **Depends on:** T11, T12
- **Build:** `vault/consistency/generic_broll.py`; `shared_global` cache resolution first; `vault/tasks.py` — on cache miss return placeholder immediately + enqueue **Cloud Tasks** background Veo job under a **Firestore-transaction single-flight lock** on the dedupe key; a **Cloud Run worker HTTP handler** (OIDC-authenticated) that Cloud Tasks invokes to run the Veo job and write the vault entry (the queue is provisioned in T00.5); swap the clip in on next resolve/prefetch.
- **Done when:** a deep-dive plays instantly on a still placeholder while Veo runs in background; concurrent identical requests trigger one generation; the clip swaps in later.

#### T28 · Procedural deepening loop `[news]`
- **§refs:** §4.5 · **Depends on:** T25, T26, T27 (mini-ingest reuses T08, mini-plan reuses T10, merge reuses T25's upsert)
- **Build:** `vault/procedural.py` — on a deep-dive `user_choice` with no bit yet: bounded loop (retrieve → mini-ingest → mini-plan `DeepDive` bit → lazy vault-gen), capped by `graph_policy.max_depth` (default 3), **shared single-flight cache keyed by topic path** (`crash/why/geopolitics`); append generated bits to the persistent Bit Graph.
- **Done when:** drilling crash→why→geopolitics generates+caches bits once and shares them; depth stops at max_depth; a second user reuses the cached branch.

#### T29 · Scheduler (daily bulletin job) `[news]`
- **§refs:** §10 (Cloud Scheduler → Cloud Run job, interest set, date idempotency) · **Depends on:** T25, T26, T27 (bulletin vault)
- **Build:** `scheduler/bulletin_job.py` — a Cloud Run **job** invoked by **Cloud Scheduler** cron; supplies the interest set as input profile; ingests today's feeds, merges Brain (§4.5), pre-plans the hub bulletin; **date-keyed idempotency** (`bulletin/<yyyy-mm-dd>`, content-keyed upserts converge on re-run).
- **Done when:** a scheduled (or manually-triggered) run produces today's bulletin; a re-run for the same date converges without duplication.

#### T30 · ▣ Milestone 3: News demo end-to-end `[news]`
- **§refs:** VERTICALS §6; §2.2 News config · **Depends on:** T19, T25–T29 (incl. **T26.5** News compositions)
- **Build:** wire the daily bulletin: interest-filtered items, wiki-web drill-down (procedural), audio-visual **and** audio-only modes, citations via grounding.
- **Done when:** a personalized 9 AM bulletin plays; different interests → different item sets (same order); drilling deeper generates+caches; audio-only works; a fact past `valid_until` is served stale + marked "true until…" and dropped at the next scheduled rebuild (self-updating). **Third shippable demo.**

### Phase 7.5 — Ask-a-character + Comic (flagship Demo 0)

#### T28.5 · Ask-a-character (grounded Q&A + claim guard) `[all; Comic/Ads/News]`
- **§refs:** §4.6, §1.2 (grounding = claim guard), §6 (`/ask`) · **Depends on:** T12, T27, T28 (reuses lazy vault + procedural loop), T17
- **Build:** `POST /session/:id/ask { question }` — retrieve the grounded Brain nodes for the question → answer **in character, only from `canon` facts**; **claim guard:** if unanswerable from verified facts, return `{ refused, reason }` (never fabricate); where the vertical permits, produce an explicitly **`imagined`** answer bit. Stream the text answer first, then materialize a bit via the procedural loop (§4.5) + lazy vault-gen (§4.4), cached by topic path. Frontend `ask/AskBox.tsx` — an input in the player; renders the streamed answer + new panels, or the refusal.
- **Done when:** a grounded question ("how did Birbal catch the thief?") returns an in-character answer + a new panel; an unverifiable question ("is it the fastest in India?") is refused; a repeat ask is an instant cache hit.

#### T29.5 · Comic composition templates + kids-mode `[comic]`
- **§refs:** §5.2/§5.6 (Comic `template_set`, panel motion), §4.4 (media kinds) · **Depends on:** T14, T22 (character sheets), T15 (media/animation layer)
- **Build:** `compositions/{StoryPanel,DialoguePanel,QuizCard}.tsx` — `panel_still` + animated **speech bubbles** (composed, not baked) + narration VO + panel transitions; a **kids-mode** flag (reserved — the MVP has no ad-insertion mechanism, so it's a no-op guard; ad slots / brand-safety are the commercialization layer in [`BUSINESS_CASE.md`](./BUSINESS_CASE.md), roadmap). Reuse the shared media/animation layer from T15.
- **Done when:** each Comic template renders a character-consistent `panel_still` with animated bubbles; kids-mode suppresses any ad slot.

#### T30.5 · ▣ Milestone 0 (flagship): Comic demo end-to-end (Akbar–Birbal) `[comic]`
- **§refs:** VERTICALS §3; §2.2/§2.3 Comic config · **Depends on:** T22, T23 (branch_explore), T28.5 (ask), T29.5 (templates), T17 (imagined/valid_until badges)
- **Build:** wire the `comic` vertical — ingest a folk tale (**place a public-domain Akbar–Birbal tale in `samples/`**) → character-consistent panel set (`panels` + `character_sheets`) → a `branch_explore` graph with `ask_character` + **what-if → `imagined`** branches; creator approves script/panels (plan/vault gates); demo: a kid **talks to Birbal** (grounded, claim-guarded), takes a what-if (imagined badge), and flips **age_level** (simpler/harder copy, §3.2 reading-level) **/ language** with **0 panels redrawn**.
- **Done when:** a kid steers & talks to a grounded comic; what-ifs are clearly marked imagined; changing `age_level` visibly **rewords** the copy and language swaps re-render — both with zero panel regeneration. **The flagship "a comic you can talk to" demo.**

### Phase 8 — Hardening (cross-cutting)

#### T31 · Observability, secrets, CDN `[all]`
- **§refs:** §10, §10.1 · **Depends on:** Milestone 1+
- **Build:** structured logging + **Cloud Logging/Monitoring/Trace/Error Reporting** across pipeline + Session API; move all creds/config to **Secret Manager**; front GCS media with **Media CDN / Cloud CDN**; basic cost/latency dashboards (§9 targets).
- **Done when:** a pipeline run is traceable end-to-end; no secret in code/env files; media served via CDN.

#### T32 · Full dependency-diff invalidation + versioned re-verify `[all]`
- **§refs:** §2.1, §3.1 (normalizer_version) · **Depends on:** T07, all agents
- **Build:** complete the invalidation graph across all artifact types (Brain edit → dependent bits/vault/VO only; storyboard edit → vault only; **a fact past `valid_until` or changed on re-ingest → its dependent bits replan/re-render/regenerate**, §2.1/§3.1; bumping `normalizer_version` re-normalizes + re-verifies); assert unaffected clips/panels are never regenerated.
- **Done when:** targeted-edit tests prove minimal recompute; the cost thesis holds under editing.

---

## 4. Deferred / roadmap backlog (explicitly NOT in the MVP build)

Do not build these during T00–T32; they are labeled roadmap in the docs. Capture as backlog:
- **`pov_lens`** — Education Gandhi/Bose per-lens narration variants (§4.3.1, VERTICALS §5).
- **Interest-scored top-K ranking** for News item ordering (§3.2.1) — MVP is include-edges + fixed order.
- **Full entity resolution** (embedding/fuzzy/alias merge) for the persistent Brain (§4.5, §7) — MVP is key-based upsert.
- **Unbounded procedural depth** beyond `max_depth` (§4.5).
- **Managed graph DB + vector retrieval** — Spanner Graph / Neo4j + Vertex AI Vector Search + text-embeddings (§7) — MVP stores Brain as JSON in Firestore.
- **Memorystore (Redis)** session cache at scale (§7) — MVP uses Firestore.
- **Server-side MP4 export** (Open-Q #2) — MVP is `@remotion/player` only.
- **End-user auth / multi-tenant** — Cloud IAM + Firebase Auth / Identity Platform (§10) — MVP is single-project + signed URLs.
- **Cross-session viewer memory / "choices have consequences"** — characters remember a viewer across sessions; aligns with roadmap viewer-signal persona inference. MVP profile is hand-edited & stateless.
- **Live class co-viewing & voting; simulated-audience testing** — multi-user shared traversal and pre-release reaction prediction (StoryGraph additions). MVP is single-viewer.
- **Multi-format & distribution exports** — print PDF comic, WhatsApp strip, quiz/flashcards, Google Classroom / YouTube / Instagram / storefront embeds (needs server-side render, Open-Q #2).

---

## 5. Suggested first-session kickoff

1. Confirm Open-Q #1 (Veo access/quota/region) and #3 (source fetch behind proxy). **#1 gates only `cinematic`/Veo paths** (car T20, T11/T22 cinematic sub-mode, lazy-Veo T27/T28/T28.5) — the `panels` default needs no Veo; #3 gates T04.
2. Build **T00 → T00.5 → T03** (foundations + **provisioned GCP resources**) and get a green `GET /health`, a Gemini smoke call, and a browser-streamed signed URL.
3. Build **T04 → T13.5** to stand up the pipeline + session backend **and the Veo-less seed project**; verify `/session` on the seed before touching the frontend.
4. Build **T14 → T20** for the first end-to-end demo (Ads). Ship it. Then Education (T21–T24), News (T25–T30), and finally the flagship **Comic** demo (T28.5 ask-a-character, T29.5 comic templates, T30.5) — which reuses Education + News machinery.
5. Keep each ticket's "Done when" as the acceptance gate; do not start a ticket before its `Depends on` are green.

> Golden rules to hold throughout: **config not branches** (§2.2), **everything grounded** (§1.2), **generate once / re-render per viewer** (§1.1). If a ticket tempts you to break one, re-read the cited section — the design already has an answer.

---

## 6. Config fixtures → see TECHNICAL_DESIGN §2.3

The concrete `vertical.config.json` fixtures for Comic / Ads / Education / News are a **spec artifact** (the §2.2 config contract in concrete form), so they live in [`TECHNICAL_DESIGN.md`](./TECHNICAL_DESIGN.md) **§2.3**. T03 lifts them verbatim into `backend/app/config/verticals/`.
