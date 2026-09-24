# A2A — Verticals: One Engine, Many Workflows

> Companion to [`PLAN.md`](./PLAN.md), [`TECHNICAL_DESIGN.md`](./TECHNICAL_DESIGN.md), [`BUSINESS_CASE.md`](./BUSINESS_CASE.md).
> The core idea — a grounded **Brain graph** + an interactive **video (Bit) graph**, generated once and **re-rendered** per viewer — is field-agnostic. Each vertical re-shapes the *workflow* (how automated, what source, what signal, what interaction pattern) but the *engine* is identical. This doc holds the full specs for all demos — **Comic (0)**, **Ads (A/B)**, **Education (C)**, **News (D)** — each expressed as a configuration of the same core (the config contract lives in [`TECHNICAL_DESIGN.md`](./TECHNICAL_DESIGN.md) §2.2–§2.3).

---

## 1. The invariant core (never changes across verticals)

| Component | Role | Cost profile |
|---|---|---|
| **Brain** | grounded knowledge graph of the source world (entities, facts, events, provenance) | cheap (LLM) |
| **Vault** | persona-neutral generated media — **Gemini-image panels by default**, Veo clips for high-end — tagged to Brain nodes | **expensive, generate-once** |
| **Bit Graph** | the interactive video as a graph of beats + branch edges | cheap (LLM plan) |
| **Profile / Context** | editable signal that selects the path (`profile.json`) | free |
| **Remotion runtime** | programmatic client-side composition, **re-rendered per viewer** | ~free |
| **Grounding** | every bit → Brain node → source span | built-in |

**The one sentence that carries every vertical:** *the expensive step (panel/clip generation) happens once per source; every personalized, interactive variant for every viewer is a cheap re-render.* No current video-generation tool has this property — they regenerate per output.

---

## 2. The dials that vary per vertical

1. **Automation / human-in-the-loop depth** — from creative co-pilot (Ads) to fully autonomous (News).
2. **Source type & cadence** — one product page, a textbook chapter, or a live daily news feed.
3. **Personalization signal** — brand profile, learner profile + live choices, or interest profile + drill-down.
4. **Graph shape / interaction pattern** — feature-router (Ads), branch-and-explore (Education & Comic; POV-lens = roadmap), hub-and-spoke + procedural deepening (News), plus **ask-a-character** (Comic/Ads/News) and **what-if / canon-vs-imagined** branches.
5. **Generation economics** — what's generated (costly, cached) vs. what's re-rendered (cheap, per-viewer).
6. **Trigger** — on session, on-demand lesson, or scheduled bulletin.
7. **Render mode (`media_mode`)** — `panels` (**default**: Gemini-image panels animated on-device) vs `cinematic` (Veo clips, high-end / ad-production agencies).

### Comparison across the five demos

| Dial | **Comic (0: Akbar–Birbal)** | **Ads (A: car, B: earbuds)** | **Education (C: history)** | **News (D: bulletin)** |
|---|---|---|---|---|
| Source | a folk tale / one-line idea | product page + brand brief | textbook chapter / comic | live news feeds/articles |
| Automation | **medium** — creator approves script + panels | **low** — creative HITL at every stage | **medium** — teacher *accuracy* review | **full** — no human in the loop |
| Signal | kid profile (age_level, language) + **choices & questions** | `profile.json` (location, household, intent) | learner profile + **live choices** (grade, language) | interest profile + **go-deeper/stop** |
| Graph shape | branch-explore + **ask-a-character** + what-if | feature-router + drill-downs | branch-and-explore (POV-lens roadmap) | hub-and-spoke + procedural deepening |
| Render mode | `panels` | car: `cinematic` (Veo) · earbuds: `panels` | `panels` | `panels` |
| Generated once (costly) | character-consistent panel set per tale | Vault per product | Vault per chapter (character-consistent) | reusable generic B-roll + persistent Brain |
| Re-rendered (cheap) | per age-level, language, branch, question | per persona/city/language | per student, per branch, per language | per user: which items, depth, language, audio-only |
| Trigger | on-demand | page/session | on-demand (game-like) | scheduled (9 AM) + interactive |
| Grounding role | canon-vs-imagined (kids know what's true) | ad compliance / claim audit | factual accuracy | trust/citation |

Notice the signal mechanism is *the same `profile.json` + `personalization_conditional` edges* — an interest topic (`interests: [finance]`) and an ad's `location: Bengaluru` are just profile fields driving the same conditional include/route mechanism (Ads and News both use it in MVP). Education MVP does **not** use conditional routing: it branches via `user_choice` only. For Education, both lens-based conditional routing **and** per-lens narration variants (the `pov_lens` pattern) are roadmap; `grade` influences generated copy complexity via slot-binding/localization, not graph routing.

---

## 3. Demo 0 — Comic / Kids' Entertainment: "Akbar–Birbal, a comic you can talk to"

**Pitch:** paste a folk tale (or a one-line idea) → a character-consistent **comic that becomes a motion story** kids can *steer and talk to*. A child asks Birbal a question and he answers **in character, only from the facts**; takes a "what-if" branch (clearly marked **imagined**); switches language or gets it **simpler or harder** — with the *same art*. Kids mode: **ads locked off**.

### Workflow shape
- **Medium automation, creator approval.** The pipeline auto-builds the Brain, script and panels; a creator/editor signs off the **script (plan)** and the **panels (vault)** before it goes live (safety + quality for children).
- **Source → Brain:** characters (Birbal, Akbar… look/voice/personality — locked by a **character bible**, §8.2), events, places, and objects ("the story behind an object"), grounded to the tale.

### Interaction pattern — branch-explore + ask-a-character + what-if
- **Choose the path** (`user_choice`) — like Education.
- **Ask a character** (`ask_character`, TECH §4.6): free-text question → grounded answer in character; unverifiable → the **claim guard** refuses. New panels are built on the spot (procedural deepening) and cached.
- **What-if** → an explicitly **`imagined`** branch (`veracity`, TECH §3.1), so a child always knows what's true.
```jsonc
{ "id": "bit_court_intro", "template": "StoryPanel", "grounding": ["char_birbal","evt_theft"],
  "edges": [
    { "type": "user_choice", "label": "How did Birbal catch the thief?", "to": "bit_trick" },
    { "type": "user_choice", "label": "What if Akbar had said no?",       "to": "bit_whatif" },   // → imagined
    { "type": "default_next", "to": "bit_verdict" } ] }
```

### Kid profile
```jsonc
{ "age_level": 8, "language": "hi" }   // age_level → simpler/harder copy (binding, not routing)
```

### Generation economics
- **Generated once per tale:** one **character-consistent panel set** (Gemini-image `panels`, TECH §4.4/§8.2) — the costly-once step, no video model.
- **Re-rendered for every kid:** every branch, every question, every language, and *simpler/harder* are composition-time only — **0 panels redrawn**. `ask_character` deep-dives are generated once, then shared/cached.
- **Kids mode:** no ad slots (brand-safety, [`BUSINESS_CASE.md`](./BUSINESS_CASE.md)).

### What no video tool can do here
A grounded, safe, branching comic kids can **talk to** — every answer traceable, every "what-if" clearly marked imagined, in any language, at the marginal cost of a TTS call.

---

## 4. Demo A & B — Product Ads (car · earbuds)

**Pitch:** one product page → a single ad that shows *different features to different viewers, on the fly*, from a shared profile — localized to any language/city, with every claim traceable for compliance.

### Workflow shape
- **Low automation, heavy HITL.** Brand and creative control matter, so the operator reviews/edits every stage (Brain → storyboard → Vault) before render — the co-pilot model.
- **Source → Brain:** product, features→benefits, brand skin (colors/logo/tone), personas, places/cities, offers — grounded to product-page spans.

### Interaction pattern — feature-router
All feature bits are authored; the profile selects which are shown via `personalization_conditional` (generic mechanism in [`TECHNICAL_DESIGN.md`](./TECHNICAL_DESIGN.md) §3.2.1).

**Worked example — one car ad, many viewers:**

| `profile.json` | Feature bit(s) selected |
|---|---|
| `location: Bengaluru` (high rainfall) | anti-rust / anti-corrosion body |
| `location: Himachal` (fog) | high-intensity headlamps & tail-lamps |
| `household: family` | 7-seater capacity + large boot |
| `intent: economy` | fuel efficiency & running cost |

**Demo B (earbuds)** uses the identical mechanism: `intent: commuter`→battery/ANC, `age_bracket: gen-z`→style/colors, `intent: fitness`→sweat-resistance & secure fit.

### Ad profile
```jsonc
{ "location": "Bengaluru", "age_bracket": "25-34", "household": "family",
  "language": "hi", "intent": "economy", "device": "mobile" }
```

### Generation economics
- **Generated once per product:** persona-neutral media Vault (pre-generated for demo reliability).
- **Re-rendered per viewer:** persona / city / language variants are composition-time only — N markets × M personas from one Vault, no regeneration.
- **Render mode — one vertical, both paths:** the **car** demo runs `cinematic` (Veo) for a filmic product ad; **earbuds** uses the default `panels` (Gemini-image). Veo access (Open-Q #1) gates only the car variant — earbuds (and every other vertical) stays Veo-less.

### What no video tool can do here
Thousands of localized, persona-targeted variants without regeneration; every on-screen claim cited (ad compliance).

---

## 5. Demo C — Education: "Interactive History Movie"

**Pitch:** the CD/DVD audio-visual learning of the past, reborn as a *game-like, branching, grounded* animated movie. Feed in a chapter (e.g. **Modern Indian History — the Independence Movement**); a student gets a watchable animation they can *steer*.

### Workflow shape
- **High automation, low production skill required.** Students/teachers aren't editors — the pipeline auto-builds the Brain, storyboard, and Vault. The **one** human checkpoint that matters is a *teacher accuracy review* (grounding makes this fast: every scene links to the textbook line it came from). Everything else is automatic.
- **Source → Brain:** characters (Gandhi, Bose, Nehru… look + voice + personality), dated events (Non-Cooperation 1920, Salt March 1930, Quit India 1942, INA…), places, causes/effects — all grounded to textbook spans.

### Interaction pattern
- **MVP — branch-and-explore (feasible now):** an entry beat sets the arc; the student picks routes to explore, like levels in a game.
  ```jsonc
  { "id": "bit_arc_intro", "template": "SceneNarration", "grounding": ["era_1920_47"],
    "edges": [
      { "type": "user_choice", "label": "The Salt March",        "to": "bit_dandi" },
      { "type": "user_choice", "label": "Quit India",            "to": "bit_quit_india" },
      { "type": "user_choice", "label": "Netaji & the INA",      "to": "bit_ina" } ] }
  ```
- **Ideal state — POV lens (roadmap):** the *same* event bits, re-narrated through a chosen character's eyes. `profile.lens: "gandhi" | "bose"` selects a narration/emphasis variant via `personalization_conditional` — one Vault, two (or more) journeys through the same history. This is the ads feature-router mechanism applied to perspective.
  ```jsonc
  { "id": "bit_1942", "grounding": ["evt_quit_india"],
    "slots": { "vo": { "bind": "lens.narration" } },     // gandhi-voice vs bose-voice framing
    "edges": [ { "type": "personalization_conditional", "when": "profile.lens=='bose'", "to": "bit_ina" },
               { "type": "default_next", "to": "bit_independence" } ] }
  ```

### Learner profile
```jsonc
{ "grade": 9, "language": "hi", "lens": "explore",   // explore | gandhi | bose
  "difficulty": "standard" }
```

### Generation economics (the life-saver)
- **Generated once per chapter:** character-consistent animation clips + scene B-roll (Veo/Imagen with fixed character sheets & seeds). This is the hard, costly part — done a single time.
- **Re-rendered for thousands of students:** every branch a student takes, every POV, every language, every difficulty level = re-composition (narration VO, ordering, on-screen labels) over the *same* Vault. **Zero regeneration per student.**
- A per-student personalized, branching "movie" at the marginal cost of a TTS call — impossible with linear video generators, which would have to render a fresh clip per student per path.

### What no video tool can do here
Branch/POV per student without regeneration; ground every scene to the source text (so a teacher can trust it); update the chapter → the whole movie updates.

---

## 6. Demo D — News: "My 9 AM Bulletin"

**Pitch:** stop watching what an outlet decides to show you. A **fully automated**, personalized audio-visual (or audio-only) daily brief that you can **dive deeper into** like a Wikipedia web — but as video.

### Workflow shape
- **Full automation, zero HITL.** A scheduled job (e.g. 9 AM) ingests the day's stories → merges into a **persistent** entity Brain → plans a bulletin Bit Graph → serves it. No human reviews it; **grounding/citations are the trust mechanism** that replaces the human.
- **Source → Brain (persistent & incremental):** entities like *RBI, Nifty, a fault line, a cricketer* persist across days; only new events/claims are added and grounded to today's articles. This is what keeps daily generation affordable.

### Interaction pattern — hub-and-spoke + procedural deepening (wiki-web)
- **Bulletin hub:** the items matching the user's interests, in fixed plan-time order (importance/recency), ~60s each. E.g. *stock-market crash · earthquake · India cricket win.*
- **Deep-dive spokes:** any item expands on demand; each expansion can itself branch. The crash → *why?* → *geopolitics* → *war* → *finance impact* — the user goes deeper or stops, exactly like following links in a wiki graph.
  ```jsonc
  { "id": "bit_item_crash", "template": "NewsItem", "grounding": ["evt_crash_2026_09_25"],
    "edges": [
      { "type": "user_choice", "label": "Why did it crash?",     "to": "bit_crash_causes" },
      { "type": "user_choice", "label": "Geopolitical angle",    "to": "bit_geo" },
      { "type": "user_choice", "label": "What it means for me",  "to": "bit_finance_impact" },
      { "type": "default_next", "to": "bit_item_earthquake" } ] }   // no dive → next headline
  ```
- **Procedural deepening:** deep-dive bits are **lazily generated the first time any user goes there, then cached** and reused for everyone — the graph grows on demand instead of being fully pre-built.

### Interest profile
```jsonc
{ "interests": ["finance","cricket","geopolitics"],
  "format": "audio-visual",   // or "audio" — skips video compositing entirely
  "length_min": 5, "language": "en", "default_depth": "headline" }
```

### Generation economics (how full automation stays cheap)
- **Heavy Vault reuse:** generic neutral B-roll (falling ticker, quake rubble, stadium celebration) is generated rarely and reused across days *and* users.
- **Persistent Brain:** yesterday's entities cost nothing today; only net-new events need grounding.
- **Per-user bulletin = pure re-render:** which items appear, length, language, and **audio-only** mode are all composition-time selections (item *order* is fixed at plan time by importance/recency — the same for every viewer; items are selected via `personalization_conditional` include-edges on `profile.interests`, exactly the Ads mechanism). Audio-only skips video rendering altogether — the cheapest possible personalization.
- **Deep-dives = generate-once-share-many:** the first curious user pays the generation cost for a branch; every subsequent user re-renders it.

### What no video tool can do here
A personalized, self-assembling daily video brief that you can interactively drill into (wiki-as-video), automated end-to-end, with every claim cited — versus a fixed linear feed you passively consume.

---

## 7. The through-line

| | Traditional video / gen tools | A2A |
|---|---|---|
| Personalize per viewer | re-shoot / re-generate (infeasible at scale) | **re-render** (near-free) |
| Interactivity / branching | none — linear timeline | native — the video *is* a graph |
| Grounding / provenance | none | every bit → source span |
| Automation vs. control | all-or-nothing | **dial per vertical** (co-pilot → autonomous) |
| Cost of the Nth variant | ≈ cost of the 1st | ≈ a TTS call |

The demos differ in workflow; the engine does not. Comic proves "a story you can talk to" (character-consistent panels + ask-a-character); Ads prove the commercial + HITL case; Education proves generate-once-render-thousands at massive fan-out; News proves full automation + procedural graph expansion. **One Brain-graph + video-graph engine, five demos, capabilities no video generator has today.**
