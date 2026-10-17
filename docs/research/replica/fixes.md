# What competitors' users hate, and what Vachan does about it

A `replica-entrepreneur` run, 2026-10-17. It looks at the nearest AI-video products (HeyGen, Synthesia, Idomoo) through their users' own reviews, so Vachan can fix what those users complain about and position itself on it.

This is research, not marketing copy:
- **The reviewers are not our testimonials.** Their words never go on a landing page.
- **The competitors' names never go in our name, ads or store listing.**

## Sample and caveats

**160 reviews from 3 sources.** 99 of them carry star ratings. Files: [`reviews.csv`](reviews.csv), [`feedback.md`](feedback.md) (ranked by [`themes.json`](themes.json) and the skill's `reviews.py`).

| Source | Rows | How it was read |
|---|---|---|
| Trustpilot, HeyGen | 50 | The review pages (newest; 1–3 stars, pages 1–2), read with a page-reading tool. Text is as the tool returned it. **Spot-check the quotes against their links before relying on them.** |
| Trustpilot, Synthesia | 49 | Same as HeyGen. |
| Hacker News | 61 | The Algolia API, exact text. Kept only comments about AI video. Dropped 106: the Synthesia piano game, job posts and off-topic rows. |

**Gaps:**
- **Reddit's JSON endpoint returned 403**, so there is no Reddit data.
- **The App Store RSS feed had no entries** for these products.
- **Idomoo has 0 Trustpilot reviews and 2 HN mentions.** The closest per-viewer competitor is therefore barely represented: treat "personalised video" findings as thin.
- **G2 and Capterra were not read.** Enterprise buyers live there, so it is the next source to add.

**Two default themes are noisy:**
- **"Ads"** matches "I saw an AD".
- **"Teams and sharing"** matches "moderation team".

Both are ignored below.

---

## 1. What they hate

Ranked by `reviews.py` score (low stars and recent reviews weigh more).

| # | Problem | Reviews | Sources | Avg ★ |
|---|---|---|---|---|
| 1 | **Price and credit paywalls**: credits run out mid-project | 30 | 3 | 1.4 |
| 2 | **Billing, cancelling, refunds** | 18 | 2 | 1.5 |
| 3 | **Opaque moderation**: scripts rejected after hours of work, with no reason given | 12 | 2 | 1.1 |
| 4 | **Uncanny output**: lip-sync, avatar motion, "looks made with AI" | 14 | 3 | 1.6 |
| 5 | **Credits burned fixing the AI's own mistakes** | 11 | 2 | 1.6 |
| 6 | **Voice and pronunciation**: mispronounced words, voices changing mid-video | 12 | 3 | 2.0 |
| 7 | **Output not accurate or trustable**: irrelevant titles, wrong advice | 11 | 3 | 1.5 |
| 8 | **The AI agent says it made an edit when it didn't** *(thin: 1 source)* | 7 | 1 | 1.0 |
| 9 | **Small edits mean full re-generation**: 40-minute renders per fix | 6 | 2 | 2.3 |
| 10 | **No preview before paying or generating** | 5 | 2 | 1.2 |

**Quotes behind the items Vachan can act on:**

- **Moderation (#3):**
  - "Would be nice if I could have received an error message or head's up that the content I was working on would be rejected prior to spending hours on this." — [Synthesia, 1★](https://www.trustpilot.com/reviews/6a2756188a8da7f7d11f48aa)
  - "If moderation decisions can change solely based on the avatar used, without changes to content, that should be clearly documented and enforced consistently." — [Synthesia, 1★](https://www.trustpilot.com/reviews/6941dfc0e1eae017b037e76d)
- **Credits on errors (#5):** "So when it makes an error you still have to go in and repay to get what you originally wanted" — [HeyGen, 1★](https://www.trustpilot.com/reviews/6ad28c220082375dc071fab3)
- **Trust (#7):**
  - "IT IS NOT ALWAYS TRUSTABLE" — [HeyGen, 1★](https://www.trustpilot.com/reviews/6ad237fc6f95d6ccd7d32b08)
  - "It produced titles on videos that were not applicable and mispronounced words." — [HeyGen, 1★](https://www.trustpilot.com/reviews/6ac94f2bdd936a8da41d0251)
- **False confirmations (#8):** "The issue is that HeyGen repeatedly told me the requested edit had been completed when it had not." — [HeyGen, 1★](https://www.trustpilot.com/reviews/6ac310e4314cb6b92ef4f248)
- **Edit loop (#9):** "I have 8 modules with roughly 4 to 5 lessons each, so I need a reliable way to make small scene corrections." — [HeyGen, 1★](https://www.trustpilot.com/reviews/6ac310e4314cb6b92ef4f248)
- **No preview (#10):** "Unfortunately, I couldn't properly preview the finished video before committing to the additional charges." — [HeyGen, 1★](https://www.trustpilot.com/reviews/6ad131b74e1b3317e63d5f11)

## 2. What is missing

Features asked for by name. The evidence here is thinner than for complaints.

| # | Request | Reviews | Sources |
|---|---|---|---|
| 1 | **A reliable way to correct one scene without redoing the video** | 6 | 2 |
| 2 | **A warning before the work is rejected**: a pre-check, not a post-hoc block | 5 | 2 |
| 3 | **Control over emphasis and pronunciation** | 3 | 2 |
| 4 | **Translation at scale that stays correct per language** (mentions translation; not every mention is a request) | 7 | 3 |

- **Request 3:** "Sometimes the emotion and emphasis is horrible and there is no way to correct it." — [Synthesia, 2★](https://www.trustpilot.com/reviews/6a9b3cde7aa25fbf5414d81f)
- **Request 4:** "you need to make sure the player actually has all of your translations inside of it" — [Synthesia, 2★](https://www.trustpilot.com/reviews/6abe07402ba5dccc4718395f)

## 3. What is unsolved

Whole jobs the competitors ignore. These become positioning.

**Regulated and accuracy-critical content: health, finance, training, product claims.**
- These are the users whose content is rejected *for being inaccurate* even when it is approved, and who cannot verify what the AI wrote. Evidence: moderation 12 + trust 11 reviews.
- "Every video I'm trying to create for NHS England which the content has been clinically approved by NHS experts, is being rejected by Synthesia saying it's inaccurate." — [Synthesia, 1★](https://www.trustpilot.com/reviews/6a7737acfb77acdeba32a8a7)
- "...undermines trust in the platform for professional and regulated use cases." — [Synthesia, 1★](https://www.trustpilot.com/reviews/6941dfc0e1eae017b037e76d)
- **Neither product can tell the user *which sentence* is unsupported, or prove what was shown.** Vachan's claim guard and signed play-log do exactly that.

**Producing at scale: many lessons, many languages, many variants.**
- Here the cost of each fix multiplies. Evidence: edit loop 6 + credits on errors 11.
- "I bought 50,000 credits to translate an online course into 10 languages." — [HeyGen, 1★](https://www.trustpilot.com/reviews/6ad0d3cd163215c533c7d97c)
- **Vachan's generate-once/compose-per-viewer split means a variant or a text fix costs no generation.**

**Personalised per-viewer video.**
- This is Idomoo's ground, but the sample has almost nothing on it. **Thin**: it needs G2/Capterra before it can be claimed as a gap.

---

## 4. Fix plan

The top items by evidence × cheapness, each mapped to what Vachan already has. Pricing and billing (themes 1–2) go to `/replica-launch`, not here. Vachan's answer there is structural: play-time is `O(assets)`, so a variant is not billed as a render.

| # | Build or change | Size | Skill / owner | Evidence | Builds on |
|---|---|---|---|---|---|
| F1 | **Grounding pre-check in the studio.** Before any generation, every script line is shown as supported or unsupported against the source, with the span. This is the "heads-up before spending hours". | M | replica-build (frontend) | moderation 12, no-preview 5, trust 11 | Gate 1 `POST /v1/gates/{run_id}/ground` exists with no screen; the mechanical verifier in `services/guard.py` |
| F2 | **Zero-cost edit meter.** Every studio edit shows "generation cost of this change: 0 s" when it only touches text, price or locale layers. A plate change shows its content-addressed cost before it runs. | S | replica-build | credits on errors 11, edit loop 6, no-preview 5 | Text-is-a-layer rule; content-addressed vault |
| F3 | **Proven edits.** After an edit, show the manifest diff (which beat and which field changed, old → new) instead of a chat claim that it was done. | S | replica-build | false confirmations 7 *(thin)*, edit loop 6 | Manifest versions; the play-log chain |
| F4 | **A refusal that explains itself.** Every refusal names its §30 type, says what the source does say, and says what source would be needed. Make the reason the headline. | S | replica-design | moderation 12 (reasonless rejection is the core complaint) | `refusal_type` and `reason` already in the response; `QuestionPanel` shows the type header |
| F5 | **Pronunciation lexicon per locale.** Fixed phonemes for the product name, ₹ figures and city names, applied at TTS build time and checked in the build log. | M | replica-backend | voice/pronunciation 12, emphasis 3 | `pipeline/tts.py` SSML scaffold |
| F6 | **Per-language completeness check.** The build fails if any beat lacks a string for a declared locale. The player then never ships a missing translation. | S | replica-test | translation 7 mentions, 3 sources | Manifest locales; schema tests |
| F7 | **No talking avatar on purpose.** This is positioning, not a build: persona-neutral stills and clips, with text as layers, sidestep the lip-sync complaints entirely. Say so in the pitch. | — | replica-brand | uncanny output 14, 3 sources | §0 "runtime, not a renderer" |

Rows F1–F6 are in [`features.csv`](features.csv) with `original = no`.

**Recommended order:**
1. **F4 and F2:** small, on the demo path, and they make the guard's value visible.
2. **F1:** the studio review screen that was already open in `HANDOFF.md`.
3. **F3.**
4. **F5 and F6:** only if the hi-IN demo shows a mispronunciation.

None of these is a new task until it is proposed and marked `GO` in `PLAN_TRACKER.md`.

---

## 5. Positioning angles

**A. Accuracy-critical teams** *(recommended)*

> For teams whose videos must be accurate (product claims, training, health) and who are tired of AI tools that invent things or reject their work without saying why, **Vachan** shows every claim with the source sentence behind it, refuses on screen what the source doesn't support, and signs a record of what each viewer saw.

Evidence: moderation 12 + trust 11 + false confirmations 7 = 30 reviews across 3 sources, average ★ 1.0–1.5.

**B. Producing at scale**

> For anyone producing many variants (languages, cities, prices, lessons) who keeps paying again to fix one scene, **Vachan** generates the pictures once and composes each version in the viewer's browser, so a text or price change costs no generation.

Evidence: credits on errors 11 + edit loop 6 + no preview 5 = 22 reviews across 2 sources.

**C. Real footage, not avatars**

> For marketers who don't want their ad to "look made with AI", **Vachan** uses real product pictures with typographic layers instead of a talking avatar.

Evidence: uncanny output 14 + voice 12 reviews across 3 sources.

**Why A:**
- It is the claim guard: already the plan's headline mechanism (AGENTS.md §1) and the one sentence a judge repeats.
- It has the most low-star evidence across the most sources.
- It is the gap neither large competitor can close without rebuilding: they generate pixels per request, so they cannot cite a span for each sentence.
- B is the strongest *supporting* line ("generated once, composed per viewer").
- C is a defensive answer for Q&A, not a lead.

Next skill in the replica chain: `/replica-brand`, driven by angle A.
