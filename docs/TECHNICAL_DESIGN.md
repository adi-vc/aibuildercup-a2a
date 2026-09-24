# A2A — Technical Design

> Companion to [`PLAN.md`](./PLAN.md) (and [`VERTICALS.md`](./VERTICALS.md) for per-vertical workflows). This document goes deep on the architecture, data model, agent design, generation/composition split, grounding mechanism, APIs, storage, consistency, latency, and deployment. It is the "how it actually works" reference.

---

## 1. Design principles

1. **Generate rarely, compose constantly.** Veo generation is expensive, slow, and hard to make consistent. So we generate a small, **persona-neutral** corpus *once* (the Vault) and push *all* variation into a cheap, deterministic, client-side composition layer (Remotion). Personalization must never require a new Veo call.
2. **Everything is grounded.** No text, claim, or scene appears in output unless it traces to a Brain node, which traces to a source span. Grounding is a first-class field, not an afterthought.
3. **The video is a graph, not a timeline.** The unit of authoring is a **Bit** (a beat). Bits connect into a directed graph with branch edges. A "played video" is a *traversal* of that graph under a Personalization Context.
4. **Lazy materialization.** Only the bits the viewer is heading toward get bound/composited. Branches materialize on demand, with lookahead prefetch.
5. **Separation of concerns:** *Brain* = what is true about the world. *Bit Graph* = how we tell it. *Vault* = raw media to tell it with. *Context* = who we're telling it to.
6. **Human-in-the-loop by default.** The pipeline is a sequence of *drafts a human can veto*. Every agent stage (ingest → enrich → plan → vault) emits an editable artifact and pauses at a checkpoint; the operator accepts, edits, or augments it (beats, features, characters, seed images) before the next stage runs. Automation does the work; the human keeps the steering wheel. This is a hard requirement, not a nice-to-have — it's what prevents polished-but-wrong output from reaching render.

---

## 2. Component architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                          BACKEND (Python / FastAPI, Cloud Run)       │
│                                                                      │
│  ┌────────────┐   ┌────────────┐   ┌──────────────┐   ┌───────────┐  │
│  │ Ingest     │──▶│ Enrich     │──▶│ Planner      │──▶│ Vault      │  │
│  │ agent      │   │ agent      │   │ agent        │   │ builder    │  │
│  │ (Gemini)   │   │ (Gemini)   │   │ (Gemini FC)  │   │ (Veo/Imagen)│ │
│  └────────────┘   └────────────┘   └──────────────┘   └───────────┘  │
│        │                │                 │                  │        │
│        ▼                ▼                 ▼                  ▼        │
│   Brain graph JSON ─────────────────▶ Bit Graph JSON    GCS Vault    │
│        (Firestore/GCS)                (Firestore/GCS)   (clips/stills)│
│                                                                      │
│  Session API: resolve Context → bind bits → serve manifest + signed  │
│  media URLs → advance traversal on branch events                     │
└───────────────────────────────┬──────────────────────────────────────┘
                                 │  REST/JSON + signed GCS URLs
                                 ▼
┌────────────────────────────────────────────────────────────────────┐
│                     FRONTEND (React + TS + Vite)                     │
│  InteractivePlayer  ── traversal state machine, prefetch, branch UI  │
│  Remotion Player    ── composition runtime (canvas/DOM), per-bit      │
│  Compositions       ── Hook / Feature / Benefit / City / CTA templates│
│  Personalize layer  ── binds Context → template props (text/VO/skin)  │
│  GroundingPanel     ── bit → Brain node → source span inspector       │
│  Studio             ── review/edit Brain, storyboard, Vault; approve  │
│  ProfilePanel       ── edit profile.json → live feature re-render     │
└────────────────────────────────────────────────────────────────────┘
```

**Scheduled entry (News):** a **Cloud Scheduler** cron → **Cloud Run job** invokes the same Ingest→Enrich→Plan→Vault pipeline unattended for the daily bulletin (§10, §4.5); interactive sessions then hit the Session API exactly as other verticals do.

---

## 2.1 Human-in-the-loop workflow (checkpoint state machine)

The backend is a resumable state machine: `INGESTED → ENRICHED → PLANNED → VAULT_READY → LIVE`, implemented with **LangGraph** — its persistent **checkpointer** gives resumability and its **interrupt** primitive implements the HITL gates (pause → operator acts → resume), so we don't hand-roll the state machine. LangGraph *orchestrates* the Gemini/Vertex AI agents as nodes over shared state; it's an OSS framework layer, not a substitute for a Google service. Each transition is produced by an agent and **gated by a checkpoint**. At a checkpoint the operator (via Studio) can:

- **Accept** the draft as-is → advance.
- **Edit** the artifact directly — rename/merge/delete Brain nodes and fix provenance; reorder/add/drop storyboard beats and branch conditions; choose which features get Veo clips; swap copy.
- **Augment** with their own input — seed images for the Vault, character/spokesperson ideas, extra beats, or brand assets — which are merged into the artifact and (optionally) re-run the agent with that guidance.

Artifacts are versioned. Re-running a stage does **not** blanket-invalidate everything downstream; invalidation is a **dependency diff** so the generate-once cost thesis holds.

**Invalidation = dependency diff.** Each downstream artifact records the input keys it derived from (a Brain node id, a `depicts` tag set, a normalized prompt hash). On an edit we diff old vs new inputs and recompute **only** artifacts whose inputs actually changed:

- Bit-Graph bits whose `grounding` set changed → replanned; other bits kept.
- Vault entries are keyed by `(normalized-prompt-hash, sorted depicts)` (§4.4). An edit invalidates only entries whose key inputs changed (e.g. a renamed feature that appears in `depicts`). Those entries are marked `stale` but **retained** (still served) until a rebuild replaces them; **unaffected Veo clips are never regenerated.**
- VO/caption caches keyed by `(bit,lang,text_hash)` (§5.3) recompute only when the bound text changes.
- A Brain fact past its `valid_until`, or changed on re-ingest, invalidates the bits grounded on it → they replan/re-render/regenerate (the mechanism behind self-updating News, §4.5).

So editing one feature's copy re-renders that bit's VO and, at most, re-generates the one clip whose prompt/`depicts` changed — not the Vault. Nothing reaches render (`LIVE`) without passing every gate. In the MVP the gates can be auto-accepted for a fast path, but the edit surface is always present.

> **Three "graphs," don't conflate:** the **LangGraph** graph orchestrates the *agent pipeline* (this section); the **Brain** is the *knowledge graph* (§3.1, stored in Firestore → Neo4j/Spanner Graph); the **Bit Graph** is the *video graph* (§3.2). Different layers, different stores.

---

## 2.2 Core parameterization — how one engine becomes each vertical

The pipeline hardcodes **nothing** about a vertical. A single `vertical.config.json` selects behaviour at each stage; a "demo" is just a config. Each core component reads exactly the params below, with the differences expressed as parameters rather than branches in code. **All four verticals — Comic, Ads, Education, News — are MVP build targets**; every enabling mechanism marked MVP below is buildable now. Two dimensions are **cross-cutting** rather than per-vertical: **`vault_policy.media_mode`** — `panels` (the **default**: Gemini-image keyframe panels animated on-device — cheapest, most character-consistent, "0 images redrawn") vs `cinematic` (Veo clips, an opt-in **high-end** path, e.g. ad-production agencies) — and the node/bit fields **veracity** (`canon|imagined`) and **fact validity** (`valid_until`), see §3.1. A small set of sub-mechanisms is genuinely deferred and labelled **(roadmap)** — see the MVP/roadmap column of the config table and the roadmap callouts in §3–§8: `pov_lens` (Education "ideal state"), full entity-resolution merge, and unbounded procedural depth beyond the configured max.

```jsonc
{
  "id": "ads | education | news",
  "source_adapter": "web_url | pdf_chapter | comic | news_feed",   // → Ingest: pluggable fetch/parse
  "brain_schema": {
    "node_types": ["…"],                                           // → Ingest/Enrich prompts (open vocab)
    "persistence": "per_source | persistent_incremental"           // → Brain store (news reuses across days)
  },
  "hitl": {                                                        // → Checkpoint state machine (§2.1)
    "gates": { "ingest": "review|auto", "enrich": "review|auto",
               "plan": "review|auto", "vault": "approve|auto" }
  },
  "profile_schema": { "fields": ["…"] },                           // → profile.json (§3.4) + runtime
  "graph_policy": {                                                // → Planner strategy
    "pattern": "feature_router | branch_explore | hub_spoke | pov_lens (roadmap)",
    "interaction": { "user_choice": true, "procedural_deepening": false, "ask_character": false, "max_depth": 3 },
    "conditional_over": ["profile.…"]                              // fields that drive routing (§3.2.1)
  },
  "vault_policy": {                                                // → Vault builder (§4.4)
    "generation": ["prebuild_all | lazy_on_demand | reuse_global"],  // ordered list, primary first; News = ["reuse_global","lazy_on_demand"]
    "media_mode": "panels | cinematic",                      // default panels (Gemini-image panels, §4.4/§8); cinematic = Veo (high-end)
    "consistency": "product_anchor | character_sheets | generic_broll",
    "cache_scope": "per_source | shared_global"
  },
  "output_modes": ["audio_visual", "audio_only"],                  // → Runtime compositor
  "template_set": ["…"],                                           // → available compositions (§5.2)
  "trigger": "on_session | on_demand | { schedule: '<cron>' }"     // → how a run starts
}
```

**Who reads what:** the Ingest agent loads `source_adapter` + `brain_schema.node_types`; the checkpoint state machine (§2.1) loads `hitl.gates`; the Planner loads `graph_policy` (its `pattern` selects a planning prompt/strategy, `conditional_over` the routing fields); the Vault builder loads `vault_policy`; the Runtime loads `profile_schema`, `template_set`, `output_modes`; the scheduler loads `trigger`.

**The intended demos, expressed purely as config (this table is all that differs between them):**

| Param | Comic (0) | Ads (A/B) | Education (C) | News (D) | MVP / roadmap |
|---|---|---|---|---|---|
| `source_adapter` | `web_url` (tale / one-line idea) | `web_url` | `pdf_chapter` / `comic` | `news_feed` | MVP (all adapters) |
| `brain_schema.node_types` | Character, Event, Place, Object, Theme | Product, Feature, Benefit, Brand, Persona, Place, Offer | Character, Event, Place, Concept, Cause | Entity, Event, Claim, Topic | MVP |
| `brain_schema.persistence` | `per_source` | `per_source` | `per_source` | `persistent_incremental` | MVP; **entity-resolution merge = roadmap** (MVP = key-based upsert, §4.5) |
| `hitl.gates` | plan `review` + vault `approve`, rest `auto` | all `review` | ingest/plan `review` (accuracy), rest `auto` | all `auto` | MVP |
| `graph_policy.pattern` | `branch_explore` | `feature_router` | `branch_explore` | `hub_spoke` | MVP; **`pov_lens` = roadmap** (§4.3) |
| `graph_policy.interaction` | choice + `procedural_deepening` + **`ask_character`** | choice + conditional + **`ask_character`** | choice only | choice + conditional + `procedural_deepening` + **`ask_character`** | MVP; **depth beyond `max_depth` = roadmap** (§4.5) |
| `graph_policy.conditional_over` | — (`age_level` = binding) | location, household, intent | — (roadmap: lens) | interests | MVP; **Education routing = roadmap**; News interest include-edges MVP, **top-K ranking = roadmap** |
| `vault_policy.generation` | `prebuild_all` + `lazy_on_demand` | `prebuild_all` | `prebuild_all` | `reuse_global` + `lazy_on_demand` | MVP (§4.4) |
| `vault_policy.media_mode` | `panels` | `panels`; **car demo → `cinematic`** (Veo) | `panels` | `panels` | MVP; **`cinematic` (Veo) = opt-in high-end**, a per-project override (§4.4/§8) |
| `vault_policy.consistency` | `character_sheets` | `product_anchor` | `character_sheets` | `generic_broll` | MVP (§8) |
| `vault_policy.cache_scope` | `per_source` | `per_source` | `per_source` | `shared_global` | MVP |
| `output_modes` | `audio_visual` + `audio_only` | `audio_visual` | `audio_visual` | `audio_visual` + `audio_only` | MVP (§5.5) |
| `trigger` | `on_demand` | `on_session` | `on_demand` | `{ schedule: "0 9 * * *" }` | MVP (§10 scheduler) |

**Cross-cutting node/bit fields (not per-vertical config, §3.1):** **`veracity`** (`canon|imagined` — real vs "what-if", used most by Comic/Education what-ifs and News speculation) and **`valid_until`** (fact expiry — powers self-updating News). Both are surfaced in the grounding panel and feed dependency-diff invalidation (§2.1).

Concrete per-demo narratives (worked examples, profiles, interaction) live in [`VERTICALS.md`](./VERTICALS.md); the table above is the contract that keeps them all the *same* engine.

---

## 2.3 Concrete per-vertical configs (`vertical.config.json`)

The four files that instantiate the §2.2 contract — the config *is* the spec, so they live here; T03 in [`IMPLEMENTATION_PLAN.md`](./IMPLEMENTATION_PLAN.md) lifts them verbatim into `backend/app/config/verticals/`. Shown as **jsonc**; the on-disk `.json` strips `//` comments and omits the commented **roadmap** fields. `BrandCard` is in every `template_set` (the universal fallback template, §4.4). `vault_policy.media_mode` defaults to **`panels`** everywhere (Gemini-image panels animated on-device); switch a vertical to `cinematic` (Veo) only for high-end use. `vault_policy.generation` is an **ordered list** (primary strategy first) — the faithful form of News's "reuse_global then lazy_on_demand".

```jsonc
// backend/app/config/verticals/comic.json   — Demo 0 (kids' entertainment: Akbar–Birbal)
{
  "id": "comic",
  "source_adapter": "web_url",                  // a public-domain tale URL, or a one-line idea
  "brain_schema": {
    "node_types": ["Character","Event","Place","Object","Theme","Source","Fact","Asset","Set"],
    "persistence": "per_source"
  },
  "hitl": { "gates": { "ingest": "auto", "enrich": "auto", "plan": "review", "vault": "approve" } },
  "profile_schema": { "fields": ["age_level","language"] },       // age_level = binding input (simpler/harder), not routing
  "graph_policy": {
    "pattern": "branch_explore",
    "interaction": { "user_choice": true, "procedural_deepening": true, "ask_character": true, "max_depth": 3 },
    "conditional_over": []
  },
  "vault_policy": { "generation": ["prebuild_all","lazy_on_demand"], "media_mode": "panels", "consistency": "character_sheets", "cache_scope": "per_source" },
  "output_modes": ["audio_visual","audio_only"],
  "template_set": ["StoryPanel","DialoguePanel","QuizCard","BrandCard"],
  "trigger": "on_demand"
}
```

```jsonc
// backend/app/config/verticals/ads.json   — Demo A/B (car & earbuds)
{
  "id": "ads",
  "source_adapter": "web_url",
  "brain_schema": {
    "node_types": ["Product","Feature","Benefit","Brand","Persona","Place","Offer","Spokesperson","Fact","Asset","Set"],
    "persistence": "per_source"
  },
  "hitl": { "gates": { "ingest": "review", "enrich": "review", "plan": "review", "vault": "approve" } },
  "profile_schema": { "fields": ["location","age_bracket","household","language","intent","device"] },
  "graph_policy": {
    "pattern": "feature_router",
    "interaction": { "user_choice": true, "procedural_deepening": false, "ask_character": true, "max_depth": 1 },
    "conditional_over": ["profile.location","profile.household","profile.intent"]
  },
  "vault_policy": { "generation": ["prebuild_all"], "media_mode": "panels", "consistency": "product_anchor", "cache_scope": "per_source" },   // vertical default; the car-ad demo overrides to "cinematic" (Veo)
  "output_modes": ["audio_visual"],
  "template_set": ["Hook","Feature","Benefit","CityOffer","CTA","BrandCard"],
  "trigger": "on_session"
}
```

```jsonc
// backend/app/config/verticals/education.json   — Demo C (interactive history movie)
{
  "id": "education",
  "source_adapter": "pdf_chapter",              // use "comic" for comic sources
  "brain_schema": {
    "node_types": ["Character","Event","Place","Concept","Cause","Source","Fact","Asset","Set"],
    "persistence": "per_source"
  },
  "hitl": { "gates": { "ingest": "review", "enrich": "auto", "plan": "review", "vault": "auto" } },
  "profile_schema": { "fields": ["grade","language","difficulty"] },   // "lens" field = roadmap (pov_lens)
  "graph_policy": {
    "pattern": "branch_explore",
    "interaction": { "user_choice": true, "procedural_deepening": false, "max_depth": 2 },
    "conditional_over": []                        // roadmap: ["profile.lens"]; grade = binding input, not routing
  },
  "vault_policy": { "generation": ["prebuild_all"], "media_mode": "panels", "consistency": "character_sheets", "cache_scope": "per_source" },
  "output_modes": ["audio_visual"],
  "template_set": ["SceneNarration","CharacterBeat","EventCard","BrandCard"],
  "trigger": "on_demand"
}
```

```jsonc
// backend/app/config/verticals/news.json   — Demo D (my 9 AM bulletin)
{
  "id": "news",
  "source_adapter": "news_feed",
  "brain_schema": {
    "node_types": ["Entity","Event","Claim","Topic","Source","Fact","Asset","Set"],
    "persistence": "persistent_incremental"       // key-based upsert (MVP); entity-resolution = roadmap
  },
  "hitl": { "gates": { "ingest": "auto", "enrich": "auto", "plan": "auto", "vault": "auto" } },
  "profile_schema": { "fields": ["interests","format","language","length_min"] },   // "default_depth" = roadmap
  "graph_policy": {
    "pattern": "hub_spoke",
    "interaction": { "user_choice": true, "procedural_deepening": true, "ask_character": true, "max_depth": 3 },
    "conditional_over": ["profile.interests"]
  },
  "vault_policy": { "generation": ["reuse_global","lazy_on_demand"], "media_mode": "panels", "consistency": "generic_broll", "cache_scope": "shared_global" },
  "output_modes": ["audio_visual","audio_only"],
  "template_set": ["NewsItem","DeepDive","Recap","BrandCard"],
  "trigger": { "schedule": "0 9 * * *" }
}
```

---

## 3. Data model

### 3.1 Brain (knowledge graph)

Stored as JSON (MVP) — a node list + edge list. One graph per source project. Nodes are **generically typed**: `type` is an open vocabulary declared per vertical in `vertical.config.brain_schema.node_types` (§2.2). The engine treats every node uniformly — `id`, `type`, `label`, free-form `attrs`, `provenance`, and `edges` — and never special-cases a vertical.

```jsonc
{
  "source": { "id": "src_1", "type": "<adapter>", "uri": "…",
              "fetched_at": "…", "text_len": 8412 },
  "nodes": [
    { "id": "n_subject", "type": "<Entity>", "label": "…",
      "attrs": { "…": "…" },
      "provenance": { "source": "src_1", "span": [102, 140], "text": "<literal source slice>" } },

    { "id": "n_attr", "type": "<Attribute>", "label": "…",
      "attrs": { "value": "…" },
      "provenance": { "source": "src_1", "span": [1204, 1249], "text": "<literal source slice>" } },

    { "id": "n_inferred", "type": "<DerivedEntity>", "label": "…",
      "provenance": { "source": "src_1", "span": [], "text": "inferred" } }
  ],
  "edges": [
    { "rel": "<relation>",         "from": "n_subject", "to": "n_attr" },
    { "rel": "<derived_relation>", "from": "n_attr",    "to": "n_inferred" }
  ]
}
```

**Node-type vocabularies are per vertical (config, not code), e.g.:**
- Ads: `Product, Feature, Benefit, Brand, Persona, Place, Offer, Spokesperson`
- Education: `Character, Event, Place, Concept, Cause, Source`
- News: `Entity, Event, Claim, Topic, Source`
- Common to all: `Fact, Asset, Set`.

**`Set` nodes (named lookup sets).** A `Set` node names a membership list that `when` expressions reference by a bare UPPERCASE identifier (§3.2.2):

```jsonc
{ "id": "set_rainy", "type": "Set", "label": "RAINY_CITIES",
  "attrs": { "members": ["Bengaluru", "Mumbai", "Cherrapunji"] },
  "provenance": { "source": "src_1", "span": [..], "text": "…high-rainfall regions…" } }
```

Sets are grounded to a source span where possible, else `inferred`. The interpreter resolves a bare UPPERCASE token in `when` to the `members` array of the `Set` node with that `label`.

**Source normalization (canonical, versioned, persisted).** Before extraction the raw source is passed through a single canonical `normalize(source)` and the result is **persisted with the source** (`source.normalized`, `source.normalizer_version`). All `span` offsets, `text` slices, and verify/repair (§4.1) are relative to this stored normalized text — never the raw source. `normalize` (v1) is deterministic:
1. HTML/markup → plain text (strip tags, decode entities, keep block boundaries as `\n`).
2. Unicode NFC normalization.
3. Collapse runs of whitespace to a single space; trim per-line; join blocks with single `\n`.

Bumping `normalizer_version` re-normalizes and re-verifies existing nodes (a dependency-diff input, §2.1).

**Provenance rule:** `span` is a `[start,end]` char offset into the **stored normalized** source text; `text` is the literal slice (for display/audit). Inferred nodes carry `span: []` and `text: "inferred"` and MUST be flagged as such in the grounding panel.

**Image-anchor provenance (multimodal).** Nodes grounded in a page image, comic panel, or product photo use an image-anchor provenance variant instead of a char span:

```jsonc
"provenance": { "source": "src_1", "image_id": "img_page3", "bbox": [x, y, w, h] }
```

`bbox` (normalized 0–1) is optional — omit it to anchor the whole image. Text-span and image-anchor provenance may coexist on one node (e.g. a captioned figure).

**Veracity — canon vs imagined.** Every node and bit carries `veracity: "canon" | "imagined"` (default `canon`). `canon` = grounded to a real source line; `imagined` = a "what-if"/hypothetical — still generated, but **never presented as fact**. The runtime shows an **"imagined" badge** and the grounding panel labels it, so (StoryGraph's phrasing) a child always knows what's true. Imagined bits are produced by what-if branches and by the ask-a-character loop (§4.6) when it steps beyond verified facts; they never satisfy the claim guard.

**Temporal validity — time-aware facts.** A fact's `provenance`/`attrs` may carry `valid_from`/`valid_until` (e.g. "price valid till Sunday", "true until March"). Expiry is evaluated at **session-resolve time** (`now > valid_until` on each grounded fact) and by the News scheduler's daily sweep — not only on edit. On the **warm path** an expired fact's bit is **served stale + UI-marked "true until …"** (never blocked); **regeneration is deferred to the cold/async path** (re-ingest → dependency-diff invalidation, §2.1). If re-ingest brings no fresh value, the bit is kept-and-marked (News drops it at the next scheduled rebuild). This is what makes self-updating News *correct*, not merely re-run daily.

### 3.2 Bit Graph (generation graph)

Generic shape — every vertical produces the *same* structure; only labels, templates, and edge mix differ (per `graph_policy`, §2.2).

```jsonc
{
  "goal": "<vertical goal>",           // sell | teach | brief — free text, guides the planner
  "entry": "bit_entry",
  "bits": [
    { "id": "bit_entry", "template": "<template from template_set>", "veracity": "canon | imagined",
      "media": { "request": { "prompt": "<neutral broll prompt>",
                              "depicts": ["<brain_node>"] } },   // kind omitted / "auto"
      // planner emits a mode-agnostic media.request; the Vault builder sets kind + patches media.vault from vault_policy.media_mode (§4.3/§4.4)
      "grounding": ["<brain_node>", "…"],          // ≥1 required
      "slots": { "headline": { "bind": "<path>" },
                 "stat":     { "bind": "<path>", "suffix": "<unit>" },
                 "vo":       { "bind": "language" } },
      "edges": [
        { "type": "personalization_conditional", "mode": "route", "when": "<expr over profile.*>", "to": "bit_a" },
        { "type": "user_choice", "label": "<button text>", "to": "bit_b" },
        { "type": "default_next", "to": "bit_c" } ] }
  ]
}
```

**Edge types:**
- `default_next` — linear advance.
- `user_choice` — renders a clickable branch button (`label` shown).
- `personalization_conditional` — auto-followed based on the **profile** (`when` expression over `profile.*`). Carries an optional `mode` field (default `"route"`) that selects one of two evaluation semantics (§3.2.1):
  - `mode: "route"` — router semantics: among all `route` conditionals on a bit, the **first** whose `when` is true is the single auto-path; if none match, fall through to `default_next`. (Ads feature_router.)
  - `mode: "include"` — filter semantics: each `include` edge is evaluated **independently**; **every** edge whose `when` is true contributes its target to the surviving set (not mutually exclusive); non-matching targets are pruned. (News hub_spoke item selection.)

**Slot binding grammar (MVP).** `bind` is a dotted path `<root>.<field>` resolved against a **bind scope** assembled per bit at resolve time. The scope is **explicitly extensible** (a vertical may add roots via `profile_schema`/`brain_schema`); the documented roots are:

- **Profile roots:** `profile` (raw fields) plus **profile-derived** roots hoisted for convenience — `language`, `lens`, `interests` (i.e. `lens.narration` ≡ `profile.lens`-selected narration node; `interests` ≡ the profile interest list).
- **Grounded-node roots:** `persona, feature, benefit, city, brand, offer` (Ads), `character, event, concept` (Education), `entity, topic, claim` (News) — each maps to a node **grounded by this bit**.

**Scope-key → node resolution.** A bit's `grounding` is a node *list*. A root key (e.g. `benefit`) resolves to the **first grounded node whose `type` matches that key** (first-of-type). If a bit grounds two nodes of the same type, resolution is **first-wins by `grounding` order** and the backend emits a validation warning at plan time (the planner should instead ground one node per bit-typed slot, or split the bit). A path that resolves to no node is a hard bind error surfaced at the checkpoint.

**bind → localize → cache pipeline.** For each slot: (1) resolve the source-language value from the scope; (2) if the field is translatable and `profile.language` ≠ source language, call **Gemini** to translate; (2b) if the vertical exposes a **reading level** (`profile.grade` / `difficulty` / `age_level`), Gemini **rewrites the copy to that level** (simpler/harder) — this is what powers Education `difficulty` and Comic `age_level`; (3) render **TTS** for VO slots. **Translatable:** all text fields (`headline`, `label`, `vo`, `caption`, `suffix`/unit strings). **Not translatable:** numeric `stat.value` (kept as-is; its `suffix`/unit *is* translated and its number formatted per locale). Cache key for a bound-then-localized string = `(node_id | profile_path, field, source_text_hash, target_lang, reading_level)`; VO adds voice → `(bit_id, lang, text_hash)` (§5.3). Optional `suffix`/`prefix`/`format` modifiers apply after localization.

#### 3.2.1 Conditional routing (the core personalization move)

The graph is authored once with **all** branch bits present; the **profile** decides which are traversed. A bit fans out via `personalization_conditional` edges evaluated against `profile.json` — the fields they key on are declared in `graph_policy.conditional_over` (§2.2). Each edge's `mode` selects the semantics:

```jsonc
{ "id": "bit_router", "template": "<template>", "grounding": ["<node>"],
  "edges": [
    { "type": "personalization_conditional", "mode": "route", "when": "<expr_1 over profile.*>", "to": "bit_x" },
    { "type": "personalization_conditional", "mode": "route", "when": "<expr_2 over profile.*>", "to": "bit_y" },
    { "type": "default_next", "to": "bit_default" } ] }
```

**Two modes (evaluated per §6.1):**
- **`route` (default)** — among all `route` conditionals on the bit, evaluate in author order; the **first** whose `when` is true is the single auto-path; if none match, `default_next`. This shows different features to different viewers (Ads feature_router).
- **`include`** — each `include` conditional is evaluated **independently**; every edge whose `when` is true keeps its target, the rest are pruned; surviving targets are re-stitched into the `default_next` chain in fixed plan-time order (News hub_spoke item selection, §4.3.1/§6.1). Not mutually exclusive — so first-match-wins does **not** apply.

Roadmap: score candidates against the profile and sequence the top-K (interest-scored ranking). **This one mechanism expresses ad feature-selection and news interest-filtering alike (POV-lenses = roadmap for Education)** — see [`VERTICALS.md`](./VERTICALS.md) for each demo's concrete instantiation.

#### 3.2.2 The `when` expression language (sandboxed)

`when` is a **tiny sandboxed expression language** evaluated by a hand-written recursive-descent parser + tree interpreter. There is **no `eval`**, no function calls, no attribute/property access beyond the whitelisted roots, and no side effects — it only reads the profile and Brain `Set` members and returns a boolean.

**Grammar (EBNF):**
```
expr    := or ;
or      := and ( "||" and )* ;
and     := not ( "&&" not )* ;
not     := "!" not | comp ;
comp    := primary ( ("==" | "!=" | "<" | ">" | "<=" | ">=" | "in") primary )? ;
primary := "(" expr ")" | path | literal ;
path    := "profile" ("." IDENT)+ ;          // only profile.* is readable
literal := STRING | NUMBER | "true" | "false" | SET_IDENT ;
SET_IDENT := /[A-Z][A-Z0-9_]+/ ;             // bare UPPERCASE → Set node members (§3.1)
```

**Semantics & sandbox rules:**
- The only readable variable root is `profile.*`; any other identifier that is not a bare UPPERCASE `SET_IDENT` or the literals `true`/`false` is a **parse error** (fail closed → edge does not match).
- `in` tests left-scalar membership in a right-hand array; a `SET_IDENT` resolves to the `members` array of the `Set` node with that `label` (unknown set → parse error). Example: `profile.location in RAINY_CITIES`.
- Comparisons are type-checked: string↔string, number↔number; a type mismatch is a non-match (not a crash). Missing `profile` field → `undefined`, which is unequal to everything and not `in` anything.
- Evaluation is total and side-effect-free; any error yields `false` so a malformed edge can never crash traversal or match unexpectedly.

**Examples:** `profile.household == "family"`, `profile.age >= 18 && profile.language == "hi"`, `profile.location in RAINY_CITIES`, `"finance" in profile.interests`.

### 3.3 Vault entry

```jsonc
{ "id": "clip_phone_outdoor", "kind": "veo_clip",
  "uri": "gs://a2a-vault/src_1/clip_phone_outdoor.mp4",
  "duration_s": 6, "aspect": "9:16",
  "prompt": "hand holding generic wireless earbuds case outdoors, soft daylight, no text, no logos",
  "depicts": ["prod_x9", "feat_battery"],           // Brain node tags
  "neutral": true,                                   // no persona/lang/brand baked in
  "seed": 42, "model": "veo-3", "created_at": "…" }
```

**Neutrality contract:** vault media contains **no on-screen text, no logos, no language, no persona cues**. Those are added only in composition. This is what lets one clip serve every persona/language/city.

**Media kinds.** A vault entry's `kind` is one of `panel_still` (a Gemini-image panel — the `panels` default, §4.4/§8), `veo_clip` (the `cinematic` mode), `imagen_still`, or `brand_card` (fallbacks). The neutrality contract holds for all — **no speech-bubble or caption text is drawn into a panel/clip; text is a composition layer** (§5), so switching language never means redrawing art (StoryGraph's "text is a layer, not pixels" — and it makes captions screen-reader-native for free).

### 3.4 Profile (`profile.json`) — the editable Personalization Context

The Personalization Context is an open key/value document; the **fields a given vertical exposes are declared in `vertical.config.profile_schema`** (§2.2). The runtime re-renders on any change. **No selection or inference in the MVP** — it's hand-edited (or, for scheduled verticals, supplied by the `trigger`).

```jsonc
{
  "language": "<bcp47>",     // drives localized copy + TTS voice (universal field)
  "<field_a>": "<value>",    // vertical-specific, from profile_schema
  "<field_b>": "<value>"
}
```

Fields are open-ended; bit-graph `when` expressions and slot binds reference them as `profile.<field>`. Unused fields are ignored. Per-vertical field sets (location/household/intent for Ads, grade/lens for Education, interests/format for News) are documented in [`VERTICALS.md`](./VERTICALS.md).

---

## 4. Agents (Gemini on Vertex AI)

All agents use the `google-genai` SDK against Vertex AI, with **structured output** (response schema) so we get validated JSON, not prose. The planner uses **function calling** to iterate. The pipeline — and the procedural-deepening loop (§4.5) — is orchestrated by **LangGraph** (§2.1), which wraps these Gemini calls as graph nodes with shared state, cycles, and HITL interrupts. Every agent's output is a **checkpointed draft** the operator can edit (see §2.1); agents accept an optional `guidance` input (free-text operator direction + seed images) that biases the next run.

### 4.1 Ingest agent (`agents/ingest.py`)
- **In:** the **stored normalized** source text (canonical `normalize(source)`, §3.1, run once and persisted) + page images (multimodal).
- **Source adapters (per `source_adapter`, all Google-native):** `web_url`/`news_feed` fetched by a **Cloud Run** fetcher; `pdf_chapter` (textbooks) parsed with **Document AI** (layout + OCR) before normalization; `comic`/image sources read via **Gemini** multimodal on Vertex AI (with **Cloud Vision** OCR where dense text needs extracting). Every adapter emits the canonical normalized text + image set that grounding runs against.
- **Task:** extract `Product/Feature/Fact/Event/Asset` nodes and their edges, each with `provenance.span` computed against the normalized text (or an image-anchor for image-grounded nodes, §3.1).
- **Output schema:** the Brain node/edge JSON.
- **Grounding enforcement (verify + repair loop):** the model must return the literal `text` slice; the backend then verifies and repairs precisely:
  1. **Exact:** if `normalized_text[span[0]:span[1]] == text`, accept.
  2. **Repair by relocation:** else search the normalized text for `text`. If it occurs **exactly once**, relocate `span` to that offset and keep the node.
  3. **Drop:** if `text` is not found at all, or occurs more than once and no author-provided span disambiguates, **drop the node** (prevents hallucinated provenance). Dropped nodes are reported at the ingest checkpoint.
  - Image-anchored nodes skip span verify; their `image_id` must reference a supplied image (else drop).

### 4.2 Enrich agent (`agents/enrich.py`)
- Derives the second-order nodes the vertical needs (per `brain_schema.node_types`) — e.g. benefits/personas, causal links, or topic clusters — plus a **style/skin** (colors/font/tone/logo, or art style) and any **character/spokesperson sheets** (look descriptor + assigned TTS voice per language). Inferred nodes are explicitly marked `inferred`.

### 4.3 Planner agent (`agents/planner.py`)
- **In:** Brain graph + goal + personalization dimensions + `graph_policy` (§2.2) + the library of available composition templates (name + required/optional slots).
- **Task:** produce a Bit Graph — choose beats, order them, insert branch points, ground each bit, and declare each bit's media need as a **`media.request`** (see §4.4), not a `clip_id`.
- **Constraint:** every bit MUST list ≥1 grounding node; the planner cannot invent facts — slots may only bind to fields present on grounded nodes.

#### 4.3.1 Pattern strategies (`graph_policy.pattern`)

The `pattern` selects a planning prompt skeleton + a required output topology the backend validates. Buildable now: `feature_router`, `branch_explore`, `hub_spoke`. `pov_lens` is **roadmap** (outline only).

| Pattern | Target topology | Required edge mix | System-prompt skeleton (abridged) |
|---|---|---|---|
| `feature_router` (Ads) | 1 hook → 1 **router** bit → N feature bits → shared CTA | router fans out `personalization_conditional` (one per `conditional_over` value) + `default_next` to a fallback feature; each feature → `default_next` CTA | "Author a hook, one router keyed on {conditional_over}, one feature bit per Feature node (bind benefit/stat), and a CTA. Every feature grounded to its Feature+Benefit nodes." |
| `branch_explore` (Education) | 1 arc-intro hub → K topic bits, each with 0–N deeper `user_choice` sub-bits → return/continue | intro exposes K `user_choice` edges (one per top-level Event/Concept); each topic bit offers deeper `user_choice` stubs + `default_next` back to arc | "Set the arc in the intro; expose each major Event as a user_choice; within each, offer deeper choices for sub-events. Ground every bit to its Event/Concept node." |
| `hub_spoke` (News) | 1 **hub** bit + K candidate item bits; each item gated by a `personalization_conditional` **`mode: "include"`** edge on `profile.interests`; surviving items chained by `default_next` in a **fixed plan-time order**; each item has deep-dive `user_choice` stubs | hub → one `personalization_conditional` `mode:"include"` edge per candidate item (`when` tests `profile.interests`, e.g. `"finance" in profile.interests`) → matching items kept, non-matching pruned & the `default_next` chain re-stitched across survivors (§6.1); surviving items linked by `default_next` in a fixed importance/recency order (**same for every viewer**); each item bit: 2–3 `user_choice` deep-dive stubs (procedurally deepened, §4.5) + `default_next` to next surviving item; last survivor → recap | "Rank candidate items by importance/recency into a fixed order; one item bit each (~60s), grounded to its Event+Claim; gate each with a personalization_conditional mode:include edge on profile.interests; add 2–3 deep-dive user_choice stubs per item and a default_next to the next item." |
| `pov_lens` (roadmap) | reuse `branch_explore` event bits, add a lens-selected narration variant per bit | `personalization_conditional` on `profile.lens` selecting a `vo` narration bind; same Vault | *(roadmap)* "Given existing event bits, emit per-lens narration slots so the same clips are re-narrated per POV." Deferred: multi-lens narration authoring + validation. |

The backend validates the produced graph against the pattern's required edge mix and rejects/re-prompts on violation (e.g. a router with no `default_next` fallback).

### 4.4 Vault builder (`vault/veo.py`)

**Planner → Vault linking.** The planner never invents a `clip_id`. Each bit carries a `media.request` describing the *need*; the Vault builder resolves it to a concrete entry and patches `media.vault`:

```jsonc
"media": {
  "request": { "prompt": "falling stock ticker, abstract, no text, no logos",
               "depicts": ["evt_crash"] },                    // planner emits this (mode-agnostic)
  "vault": "clip_ticker_fall"                                    // builder patches this in
}
```

**Dedupe key** = `sha256(normalize_prompt(prompt)) + ":" + sorted(depicts).join(",")`. Builder flow per request: compute key → if an entry exists (any scope allowed by `cache_scope`), reuse its `clip_id`; else generate **per `media_mode`** (see below), store to GCS, write the entry, tag `depicts`, index by key. This same key is the invalidation unit in §2.1.

**Media mode (`vault_policy.media_mode`) — what gets generated.**
- `panels` (**default**): a **keyframe panel still** via **Gemini image ("Nano Banana") / Imagen** (kind `panel_still`), no text baked; the composition layer animates it on-device (§5.6). No video model — cheapest, most character-consistent, "0 images redrawn" across every language/persona/age variant.
- `cinematic`: a **Veo clip** (kind `veo_clip`) — filmic motion, an opt-in **high-end** path (e.g. ad-production agencies). Higher cost/latency; character consistency is harder (mitigated by §8.2). Everything downstream (dedupe, fallback, generation modes, composition) is identical — only the generator and the `kind` differ. **The planner leaves `kind` unset; the Vault builder resolves it from `vault_policy.media_mode`** (`panels`→`panel_still`, `cinematic`→`veo_clip`) so only the selected generator runs. (A cache scope is single-mode, so the dedupe key needn't encode `media_mode`.)

`media_mode` is a vertical **default, overridable per project/build** — e.g. the **car** ad demo runs `cinematic` (Veo) for a filmic product ad while **earbuds** keeps the `panels` default, so the one Ads vertical exercises both paths. (Veo access, Open-Q #1, then gates only the `cinematic` projects.)

**Missing-clip fallback (never undefined).** A bit must never reference a non-existent asset. Resolution order: (1) the deduped/generated **panel/clip** (per `media_mode`); (2) if generation is pending or failed, an **Imagen still** depicting the same `depicts`; (3) if that is unavailable, a **solid brand-skin card** (Remotion-rendered from the brand theme + headline). The resolved `media.vault` always points at a playable asset; its `kind` (`panel_still | veo_clip | imagen_still | brand_card`) tells the compositor how to render it.

**Generation modes (`vault_policy.generation`).**
- `prebuild_all` (Ads, Education): build the whole vault synchronously behind the vault checkpoint before `LIVE`.
- `reuse_global` (News): resolve `media.request` against a **`shared_global`** cache first (generic B-roll reused across sources and days); only truly-new needs generate.
- `lazy_on_demand` (News deep-dives, §4.5): **never block the viewer on raw generation.** On a cache miss the builder (a) immediately returns the fallback placeholder (Imagen still → brand card) so the bit plays now, and (b) kicks off **background generation per `media_mode`** (panel/clip) as a **Cloud Tasks** job (Cloud Run worker) under a **single-flight lock** (a **Firestore transaction** on the dedupe key, so concurrent requests for the same key await one generation). When the media lands it is written to the vault and **swapped in** on the next resolve/prefetch; in-flight sessions keep the placeholder for the current play.

### 4.5 Procedural deepening & incremental Brain (News)

**Procedural deepening** (`graph_policy.interaction.procedural_deepening: true`) grows the graph on demand instead of pre-building every branch. When a viewer takes a deep-dive `user_choice` stub that has no bit yet, a bounded on-demand loop runs **once** and caches for everyone:

1. **Retrieve** source spans relevant to the sub-topic (from today's articles / persistent Brain).
2. **Mini-ingest** → grounded nodes for the sub-topic (same verify/repair as §4.1), merged into the persistent Brain (see below).
3. **Mini-plan** a single deep-dive bit (`DeepDive` template) grounded to those nodes, with its own deep-dive stubs.
4. **Vault-gen** via `lazy_on_demand` (§4.4) — placeholder immediately, Veo in background.

- **Bounded depth:** a configurable `max_depth` (default **3**) caps how deep the wiki-web goes; a stub at `max_depth` is disabled (or shows "end of thread"). **Unbounded depth beyond `max_depth` = roadmap.**
- **Shared single-flight cache keyed by the topic path** (e.g. `crash/why/geopolitics`): the first curious user triggers the loop under a lock (**Firestore transaction**) keyed by that path; concurrent/subsequent users await and then reuse the same generated bit + clips. Cached bits are appended to the persistent Bit Graph.

**Incremental Brain merge.** For `persistence: persistent_incremental`, each daily/mini ingest merges into the persistent Brain by **key-based upsert (MVP):** normalize a merge key = `(normalized(label), type)`; matching key → update attrs + append provenance (multi-day claims accrue spans); no match → insert. **Full entity resolution** (embedding/fuzzy match, alias merging, conflict resolution) is **roadmap** (§7). This keeps yesterday's entities free and only grounds net-new events.

### 4.6 Ask-a-character (answer-time grounded Q&A + claim guard)

When `graph_policy.interaction.ask_character` is on, a viewer asks a free-text question mid-story ("Birbal, how did you catch the thief?" · "Does it handle flooded roads?"). The runtime:

1. **Retrieve** the grounded Brain nodes relevant to the question (over the project's Brain).
2. **Answer, in character, only from those grounded facts.** The **claim guard** is the grounding principle (§1.2) enforced at *answer time*: if the question can't be answered from verified `canon` facts, the character **refuses** ("I can only share verified facts") — it never fabricates. Where a vertical permits speculation, the answer is generated as an explicitly **`imagined`** bit (§3.1), never as fact.
3. **Stream, then materialize.** The text answer streams first (low latency); then a short answer bit/panel is built via the procedural-deepening loop (§4.5) + lazy vault-gen (§4.4). **Cache key = the sorted set of retrieved `canon` node-ids (+ vertical)** — so different phrasings that resolve to the same facts share one cached bit (embedding/fuzzy match of the raw question is roadmap). The answer bit plays as an **interstitial**, then returns to `currentBitId` (it's reachable via `/ask`, not a manifest edge). **Refusals are not cached** (cheap; re-runs the guard).

So ask-a-character is procedural deepening (§4.5) with a **free-text entry point + an answer-time grounding gate**. Endpoint: `POST /session/:id/ask` (§6). It powers "a comic you can talk to" (Comic), "ask the product" (Ads), and "tap a person → dated backstory" (News) — one mechanism, three verticals.

---

## 5. The composition & personalization layer (Remotion)

### 5.1 Why client-side programmatic
- **Zero-latency personalization:** swapping persona/language/city is a props change + re-render, not a network/gen round-trip.
- **Determinism & consistency:** brand skin, layout, typography, captions are code — pixel-consistent across every variant.
- **Cheap infinite variants:** N personas × M languages × K cities from one vault.

### 5.2 Composition templates (`frontend/src/compositions/`)
Each template is a Remotion composition that takes typed props and layers:
`[vault media] → [brand skin: color wash / logo] → [animated headline/stat] → [captions] → [VO audio track] → [transitions]`.

The **template set is per vertical**, declared in `vertical.config.template_set` (§2.2) — e.g. Ads: `Hook, Feature, Benefit, City/Offer, CTA`; Education: `SceneNarration, CharacterBeat, EventCard`; News: `NewsItem, DeepDive, Recap`; Comic: `StoryPanel, DialoguePanel, QuizCard`. Props are produced by the personalize layer from `bit.slots` + profile.

```ts
type FeatureProps = {
  media: VaultMedia;                 // signed URL + meta
  headline: string;                  // bound from benefit.label (localized)
  stat?: { value: number; suffix?: string };
  voAudioUrl: string;                // Cloud TTS output for the language
  brand: BrandSkin;                  // colors/font/logo
  captions: Caption[];               // timed, from VO
};
```

### 5.3 Localized VO
- On session resolve, backend renders VO per bit with **Cloud Text-to-Speech (Chirp)** using the spokesperson's assigned voice for the Context language; caches by `(bit_id, language, text_hash)` in GCS. Captions derived from TTS timepoints. (Text itself is localized by Gemini during binding, cached identically.)

### 5.4 Interactive traversal (`player/InteractivePlayer.tsx`)
- A small state machine holds `currentBitId` + `history`. The client traverses the **server-resolved manifest**, not raw edges: `personalization_conditional` edges (both `route` and `include`) are already evaluated and collapsed into the annotated `default_next` chain at manifest-build time (§6.1), so the client never applies `when`/first-match logic itself.
- On bit end: follow the manifest's annotated next edge; render `user_choice` buttons where the manifest exposes them; else `default_next`.
- **Prefetch:** as soon as a bit starts, resolve+bind its likely successors (all `user_choice` targets + the annotated next target) and preload their vault media + VO so branches play instantly.

### 5.5 Audio-only mode (`output_modes: audio_only`)

When the profile selects `format: "audio"` (News), the compositor skips video entirely and renders a **VO track + timed captions over a static brand/still card** (brand skin + the bit's headline, or the bit's Imagen still). No Veo media is fetched. **Bit duration = the TTS length** (rather than the clip length). The interaction layer is unchanged — the same edges, `user_choice` buttons, and traversal state machine apply; only the visual surface differs. This makes audio-only the cheapest personalization (VO cache hit → near-zero cost, no video decode).

### 5.6 Panel motion (`media_mode: panels`, the default)

With `panels`, the composition animates the `panel_still` on-device — Ken-Burns pan/zoom & parallax, **speech-bubble pop-in**, panel-to-panel transitions — the "motion comic". With `cinematic` it plays the `veo_clip` instead. Either way, **speech bubbles and captions are composed, never drawn into the art** (§3.3): switching language, age level or persona re-renders text over the *same* panel — "0 images redrawn" — and the composed text is translatable and screen-reader-native. This is why Comic/Education can offer "simpler or harder" and instant language swaps at no generation cost.

---

## 6. Session / API contract

```
# Pipeline (each stage is gated; PATCH lets the operator edit the draft, POST /approve advances)
POST  /ingest                 { source_uri | text, images? }        → { project_id, brain, stage:"INGESTED" }
PATCH /projects/:id/brain     { nodes?, edges? }                     → { brain }          (operator edits/merges)
POST  /enrich                 { project_id, guidance? }              → { brain }
PATCH /projects/:id/bitgraph  { bits?, edges? }                      → { bit_graph }      (reorder/add/drop beats)
POST  /plan                   { project_id, goal, guidance? }        → { bit_graph }
POST  /vault/build            { project_id, seed_images?, features? }→ { vault[] }        (choose features / seed imgs)
POST  /projects/:id/approve   { stage }                              → { stage }          (advance the state machine)

# Runtime (profile-driven)
POST /session                 { project_id, profile }                → { session_id, entry_bit, manifest }
GET  /session/:id/bit/:bitId  ?profile=…                             → { bound_bit, media_urls, vo_url, captions }
POST /session/:id/advance     { from_bit, edge }                     → { next_bit_id }
POST /session/:id/profile     { profile }                            → { manifest }       (re-render on profile edit)
POST /session/:id/ask         { question }                          → { answer_bit }  |  { refused, reason }   (grounded Q&A + claim guard, §4.6)
GET  /grounding/:project_id/:node_id                                 → { node, source_span, text }
```

`manifest` = the bit graph pruned/annotated for a profile (which edges are auto vs choice). Media served as **signed GCS URLs** so the client streams directly from the bucket.

### 6.1 Manifest pruning

Building a manifest for a profile evaluates each bit's `personalization_conditional` edges by their `mode` (§3.2/§3.2.1) — two distinct code paths:

**`route` edges (Ads router).** Evaluate the bit's `route` conditionals in author order; keep the **first** whose `when` is true as the single `auto` onward path and **drop the other `route` targets**; if none match, use `default_next`. (First-match-wins.)

**`include` edges (News hub-spoke).** Evaluate **every** `include` edge on the bit independently; **keep** targets whose `when` is true, **prune** the rest. Then re-stitch the fixed plan-time `default_next` chain across survivors:
```
survivors = [item for item in candidates_in_plan_order if item.include_when(profile)]
hub.entry_default_next = survivors[0]            // hub → first surviving item
for i in range(len(survivors) - 1):
    survivors[i].default_next = survivors[i+1]   // each survivor → next survivor
survivors[-1].default_next = terminal_bit        // last → recap/terminal
```
Order is fixed at plan time (same for every viewer); the profile only changes *which* items survive, never their sequence. If no item survives, the hub's `default_next` points straight at the terminal bit.

**Shared post-steps (both paths):**
1. **Keep all `user_choice` targets** — interactivity is profile-independent; a viewer can always branch. (Lazy/procedural targets, §4.5, are kept as stubs and materialized on click; re-stitching treats an un-materialized survivor as present — its `DeepDive`/item bit is generated on first entry.)
2. Annotate each retained edge as `auto` (route/default the runtime follows) or `choice` (button).

**Consistency with splice-forward (§6.2):** a mid-session profile edit re-runs the same per-mode evaluation and re-stitch, then splices forward from the nearest affected bit — for hub-spoke, if the surviving item set changes upstream of the current item, the chain is re-stitched from the hub and playback resumes at the first survivor at/after the current position; already-played items are not replayed.

### 6.2 Profile edit = splice forward

`POST /session/:id/profile` recomputes the manifest but **does not restart from `entry`**. Diff the new manifest against the current traversal:
- If the change only affects bits **downstream** of `currentBitId`, keep the current position and swap the forward path.
- If the change alters the path **upstream of the current bit** (a router bit whose chosen edge now differs), **re-resolve from the nearest affected router bit** on the path from entry to current — not from entry. Playback splices forward to the newly-selected branch at that router; already-played bits are not replayed.
This makes a mid-video profile edit feel like a live re-route, preserving the viewer's progress.

### 6.3 Loading & error placeholder states

While VO/media resolve, a bit is never blank:
- **Media pending** (lazy/single-flight in flight, §4.4) → show the fallback (Imagen still → brand-skin card); swap to the generated media when ready.
- **VO pending** → show captions from bound text immediately; play audio when TTS lands (or stay caption-only in audio-poor contexts).
- **Resolve error** (bind failure, missing node) → render the brand-skin card with the headline and log the error to the session; traversal still advances so the viewer is never stuck.

---

## 7. Storage & state

| Data | MVP store | Rationale |
|------|-----------|-----------|
| Brain graph | JSON in Firestore (doc per project) | queryable, small, easy edits |
| Bit Graph | JSON in Firestore | same |
| Vault media | GCS bucket `a2a-vault/<project>/…`, fronted by **Media CDN** (video) / **Cloud CDN** | large binaries, signed URLs, cached at edge |
| VO/captions cache | GCS, keyed by `(bit,lang,text_hash)` | reuse across sessions |
| Sessions | Firestore (ephemeral); **Memorystore (Redis)** at scale | short-lived traversal state |

Roadmap: swap Brain to a managed graph DB — **Neo4j** (rich Cypher/GraphRAG tooling; runs on GCP via Neo4j Aura or GKE) or **Spanner Graph** (fully Google-managed) — plus **Vertex AI Vector Search** over **Vertex AI text-embeddings** of source chunks, for retrieval-grounded extraction and fuzzy entity resolution.

---

## 8. Consistency strategy (the hard part)

- **Never bake persona/brand into Veo** — that variance lives in the deterministic composition layer, which is inherently consistent.
- **Style continuity:** brand skin (color/type/motion) is one shared Remotion theme object.

The Vault builder selects one of **three consistency policies** (`vault_policy.consistency`), each a distinct builder code path:

### 8.1 `product_anchor` (Ads)
Anchor every depicting **panel/clip** prompt with an **Imagen-generated neutral product still + a fixed `seed`** (works for both `media_mode`s); keep prompts template-stable; reuse vault media rather than regenerating. One canonical still per product keeps the object identical across panels/clips.

### 8.2 `character_sheets` (Education)
Per recurring character, the enrich agent (§4.2) produces a **character sheet**:

```jsonc
{ "character": "gandhi",
  "reference_still": "gs://…/gandhi_ref.png",   // Imagen, generated once
  "seed": 71,                                    // fixed across all clips of this character
  "look": "bald, round glasses, white khadi shawl, thin build" }  // canonical look-descriptor phrase
```

Each panel/clip depicting that character is generated **image-conditioned on `reference_still`** + the fixed `seed` + the anchored `look` phrase — with `media_mode: panels` (the default) that's a **Gemini-image panel** (kind `panel_still`), with `cinematic` it's a **Veo clip**; either way the character renders consistently across scenes.

**Multi-character in frame:** pass every present character's reference still as a conditioning image and concatenate their `look` phrases with explicit spatial/role cues ("<gandhi-look> on the left speaking to <nehru-look> on the right"); use a single deterministic `seed` derived from the sorted character-id set so the same ensemble reproduces.

### 8.3 `generic_broll` (News)
No identity anchoring — generate/reuse **generic neutral B-roll** (falling ticker, rubble, stadium crowd) tagged by `depicts` and shared via `shared_global` cache. Consistency is not required (no recurring subject); maximal reuse is the goal.

- **Spokesperson/character voice:** a single assigned TTS voice per character per language, applied uniformly (independent of the visual policy above).

---

## 9. Latency, cost, caching

- **Cold path (per project, once):** ingest+enrich+plan (~seconds of Gemini) + vault build (Veo minutes) — done offline before demo.
- **Warm path (per viewer):** session resolve = text localization + TTS render (cacheable) + signed URLs. Target < 1–2s to first frame; subsequent bits prefetched → instant.
- **Cost control:** vault dedupe; persona-neutral clips maximize reuse; VO/text caches keyed by content hash.

---

## 10. Deployment

- **Backend:** container on **Cloud Run**; Vertex AI (Gemini/Veo/Imagen) + Cloud TTS via service account; GCS bucket + Firestore.
- **Scheduler (News `trigger: {schedule}`):** a **Cloud Scheduler** cron job invokes a **Cloud Run job** (the daily bulletin builder) per the `trigger` cron. The scheduled run supplies the **interest set** as its input profile — the union of subscribers' `interests` (MVP: a configured default interest set) — so the run ingests today's feeds, incrementally merges the Brain (§4.5), and pre-plans the hub bulletin. **Idempotency:** each run is keyed by date (`bulletin/<yyyy-mm-dd>`); a re-run for the same date upserts (key-based, §4.5) rather than duplicating — Brain merge, vault dedupe (§4.4), and bit-graph keys are all content-keyed, so a retried or double-fired run converges to the same state.
- **Async generation:** background Veo/vault jobs run on **Cloud Tasks** → Cloud Run workers; single-flight locks are **Firestore transactions** (§4.4/§4.5).
- **Media delivery:** signed GCS URLs fronted by **Media CDN** (video) / **Cloud CDN** (stills/audio).
- **Secrets & config:** service-account credentials and model/API config in **Secret Manager**.
- **Observability:** **Cloud Logging, Cloud Monitoring, Cloud Trace, Error Reporting** (Google Cloud Operations) across the pipeline and Session API.
- **Frontend:** Vite build on **Firebase Hosting** (or Cloud Run static). `@remotion/player` runs entirely client-side.
- **Auth (MVP):** single project, no end-user auth; signed URLs for media. Roadmap: per-tenant isolation via **Cloud IAM**; end-user auth via **Firebase Authentication / Identity Platform**.

### 10.1 Google Cloud service map (every piece → a Google service)

The design is Google-native for every cloud service. The non-Google pieces are **framework/OSS layers** that sit *on top of* Google services, not substitutes for them: **Remotion** (client-side composition, no GCP equivalent, runs in the browser), **LangGraph** (agent-pipeline orchestration — wraps Gemini on Vertex AI), and optionally **Neo4j** (graph DB — runs on GCP, co-equal to the Google-native Spanner Graph).

| Concern | Google Cloud service | Where |
|---|---|---|
| Backend API + workers | **Cloud Run** (service + jobs) | §2, §10 |
| Agent-pipeline orchestration + HITL state | **LangGraph** (OSS; orchestrates Gemini on Vertex AI) | §2.1, §4 |
| Agent LLM (ingest/enrich/plan) + translation | **Gemini on Vertex AI** (`google-genai`) | §4 |
| Panel generation (**default** `media_mode`) | **Gemini image ("Nano Banana")** / Imagen (Vertex AI) | §4.4, §8 |
| Cinematic video (high-end `media_mode`) | **Veo** (Vertex AI) | §4.4, §8 |
| Still generation + reference sheets | **Imagen** (Vertex AI) | §4.4, §8 |
| Voiceover (localized) | **Cloud Text-to-Speech (Chirp)** | §5.3 |
| PDF/textbook parsing | **Document AI** | §4.1 |
| Comic/image OCR | **Cloud Vision** (+ Gemini multimodal) | §4.1 |
| Object storage (Vault, VO cache) | **Cloud Storage (GCS)** | §7 |
| Graph/session/state JSON | **Firestore** | §7 |
| Session cache at scale | **Memorystore (Redis)** | §7 |
| Graph DB (roadmap) | **Spanner Graph** (Google-managed) or **Neo4j** (Aura on GCP / GKE) | §7 |
| Vector retrieval + embeddings (roadmap) | **Vertex AI Vector Search** + **Vertex AI text-embeddings** | §7 |
| Scheduled bulletin trigger | **Cloud Scheduler** → Cloud Run job | §10 |
| Async gen queue + locks | **Cloud Tasks** + Firestore transactions | §4.4, §10 |
| Media/edge delivery | **Media CDN / Cloud CDN** | §7, §10 |
| Secrets | **Secret Manager** | §10 |
| Observability | **Cloud Logging / Monitoring / Trace / Error Reporting** | §10 |
| Static frontend hosting | **Firebase Hosting** | §10 |
| AuthN/Z (roadmap) | **Cloud IAM** + **Firebase Auth / Identity Platform** | §10 |

---

## 11. Open technical questions (to resolve before build)

1. **Veo access & quotas** in the target GCP project (region, model version, rate limits) — gates vault build.
2. **Remotion runtime mode:** `@remotion/player` (interactive, in-browser) vs server-side render for fallback MP4 export — MVP uses the Player; export is roadmap.
3. **Source fetching** behind restrictive networks — may need a fetch/allowlist step or manual paste for the demo.
4. **Studio edit fidelity** — how rich should the checkpoint editors be for the demo? MVP: JSON-level edit + re-run with guidance + approve; roadmap: visual graph/storyboard editors.
5. **Branch expansion depth** — resolved: procedural deepening is **in MVP** for News, bounded by `graph_policy.max_depth` (default 3) with a shared single-flight cache keyed by topic path (§4.5). *Unbounded* depth beyond the configured max, and full entity-resolution Brain merge, remain roadmap.
