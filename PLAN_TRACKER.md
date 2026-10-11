# Vachan — Plan Tracker

The running log of implementation work. It is the single source of truth for **what has been attempted, what happened, and what is safe to do next.** Tasks are drawn from the build order in [`vachan-plan.md`](vachan-plan.md) §64 (phases P0–P9) and its feature register (§15).

> New here? Read [`AGENTS.md`](AGENTS.md) first, then this file.

---

## How this works (read before touching anything)

1. **One task in flight at a time.** Never start a second task while one is `IN PROGRESS`. The whole point is a clean, reviewable trail.
2. **A task starts only after it is marked `GO`.** Proposing a task (`PROPOSED`) is not permission to build it. Work begins **only** once the status has been set to `GO` in this file. If you believe the next task is obvious, still wait for `GO`.
3. **Log as you go — especially the messy parts.** When a task is attempted, capture in its entry:
   - what was actually done (vs. what the plan said);
   - anything that **couldn't** be done, and why;
   - any **shortcut** taken (and the debt it leaves);
   - any **alternative** discovered during implementation that differs from the plan — flag it so the plan/`AGENTS.md` can be updated;
   - blockers, open questions, and follow-ups.
4. **Close before you open.** A task must reach `DONE` (or `BLOCKED`/`DEFERRED` with a reason) before the next one is proposed and given `GO`.
5. **Deviations are decisions.** If implementation reveals a better path than `vachan-plan.md`, record it here and note whether the plan was updated. The tracker is allowed to overrule the plan — but only in writing.

## Status legend

| Status | Meaning |
|---|---|
| `PROPOSED` | Written up, awaiting go-ahead. **Do not build.** |
| `GO` | Approved to start. Exactly one task should be `GO`/`IN PROGRESS` at a time. |
| `IN PROGRESS` | Being worked on now. |
| `DONE` | Complete; exit criteria met (note which, from the plan). |
| `BLOCKED` | Cannot proceed; reason + what's needed to unblock recorded. |
| `DEFERRED` / `CUT` | Intentionally postponed or dropped (e.g. via the §65 cut line); reason recorded. |

## Hosted validation register

Use [docs/HOSTED_VALIDATION_RUNBOOK.md](docs/HOSTED_VALIDATION_RUNBOOK.md) for every shared-cloud deployment or hosted-validation task. Add future hosting work here with its task ID, environment, owner, non-secret evidence, and status. Hosted work stays `DEFERRED` while local development can safely continue; use `BLOCKED` only when it prevents required progress.

| Task | Status | Environment | Validated |
|---|---|---|---|
| T1 · P0 walking skeleton | ✅ `DONE` | GCP project `a2a-ghostrider-511215` / Firebase Hosting | 2026-10-10: Source upload to GCS operational; API deployed and accessible |
| T2 · P1 Brain + Gemini | ✅ `DONE` | Firestore + Cloud Run (`a2a-ghostrider-511215`) | 2026-10-10: Gate 1 edit persisted across restart · 2026-10-11: Gemini extraction (`gemini-3.8-flash`) verified with 8 facts extracted |

## Entry template (copy this per task)

```
### T<n> — <short title>   ·   <plan ref, e.g. P1 / F3>
- Status: PROPOSED | GO | IN PROGRESS | DONE | BLOCKED | DEFERRED
- Dates: opened <YYYY-MM-DD> · updated <YYYY-MM-DD>
- Goal: <one line — what "done" means, tied to the plan's exit criteria>
- Done / changed: <what was actually built>
- Couldn't do / shortcuts: <gaps, debt, anything skipped>
- Alternative found: <if implementation diverged from the plan — and was the plan updated?>
- Blockers / follow-ups: <what's next or what's needed>
```

---

## Current task

**Nothing in flight.** T7 (P6 edges + scrubbing, placeholder clips) is `DONE`; T6 (P7.5) is `DONE`. Next is credential-bound (P7 guard, P4 Vault) or P8 accessibility. P5 was chosen over P4 because P4's exit criteria need live Gemini Image/TTS credentials that don't exist yet, while P5 needs none and carries 24 of the 75 live seconds.

## Task log

### T1 — Walking skeleton   ·   P0 / F1 F17
- Status: DONE
- Dates: opened 2026-09-30 · updated 2026-10-10
- Goal: Prove the whole pipe end-to-end with minimal content, deployed to real infrastructure.

**Exit criteria — all met:**
1. ✅ `POST /v1/sources/upload` accepts the fixture HTML, snapshots it to GCS, returns a `source_id` + 3 stub facts.
2. ✅ The `p0_single_beat` manifest renders in a browser — dark city-street SVG with "30 cm of water. Still going." overlaid as a text layer. Switching locale dropdown to `hi-IN` swaps the text without changing the image (text-is-a-layer proven in P0).
3. ✅ **Hosted validation complete (2026-10-10):** GCP project `a2a-ghostrider-511215` provisioned; Cloud Run API deployed at `https://vachan-api-rcsu47sdaq-el.a.run.app`; Firebase Hosting deployed; `POST /v1/sources/upload` with `vega_v1.html` fixture returned `source_id` and HTML stored in GCS bucket `vachan_bucket`.

**Done / changed:**
- `backend/` — FastAPI app (`main.py`, `config.py`), Pydantic models (`models/brain.py`), routers (`sources.py`, `manifest.py`), GCS service (`services/storage.py`), 6 passing tests, `Dockerfile` (multi-stage, Python 3.11-slim, non-root), `requirements.txt`.
- `backend/fixtures/` — `vega_v1.html` (authoritative Vega V1 source with all 8 §17 facts as verbatim spans; refusal-driving gaps deliberately absent) + `p0_single_beat.json` (hand-written single-beat manifest, `schema_version: "1.0"`, integrity indexes populated).
- `frontend/` — React 19 + Vite 8 + TypeScript. `src/types/manifest.ts` mirrors §28 schema. `BeatPlayer` component: plate, text layer, locale selector, fact badges (click → shows `fact_id`, `span_id`, `origin: canon`). `useManifest` hook. Vite proxy `/v1` → `localhost:8080`. `tsc --noEmit` clean; `npm run build` succeeds (224 kB bundle).
- `frontend/public/assets/placeholder_flood_street.svg` — dark city-street-in-rain SVG standing in for a real Vault plate.
- Root: `docker-compose.yml` (fake-gcs-server + API hot-reload), `models.yaml` (pinned model versions), `.gitignore`, `cloudbuild.yaml` (6-step CI/CD), `cloudrun-service.yaml`, `SKELETON.md`, `backend/README.md`, `frontend/README.md`.
- **Deployment:** `cloudbuild.yaml`, `cloudrun-service.yaml`, `frontend/.firebaserc` configured with real project IDs; Cloud Build CI/CD pipeline working.

**Couldn't do / shortcuts:**
- No real GCS bucket used locally during initial development; the docker-compose emulator (`fake-gcs-server`) was used for P0. The storage service is emulator-aware and switches to real GCS when `GCS_EMULATOR_HOST` is unset.

**Alternative found:**
- **Python 3.11 required (not 3.9).** `google-cloud-storage` pulls in `cryptography`, which needs pre-built wheels. macOS system Python 3.9 lacks them; Python 3.11 ships them. The Dockerfile uses `python:3.11-slim` to match. Not a debt — 3.11 is the correct choice — but noted here so teammates don't hit the same wheel-build failure. **No plan update needed** (the plan is model/tool-agnostic and doesn't pin a Python version).

**Blockers / follow-ups:**
- None — T1 is complete.
- Next task: **T2 — P1 Brain + span verification** (`vachan-plan.md` §64.3). This wires real Gemini extraction + the §39.1 mechanical span verifier, replacing the 3 stub facts in `brain.py`.

### T2 — Brain + span verification   ·   P1 / F2 F3 F29
- Status: DONE
- Dates: opened 2026-09-30 · updated 2026-10-01 · **hosted validation completed 2026-10-10** · Gemini integration verified 2026-10-11
- Goal: Wire real Gemini extraction + mechanical §39.1 span verifier + Firestore persistence. Exit criteria per §64.3: ≥8 facts extracted from fixture; 100% of canon facts string-verify; a deliberately corrupted fact demotes to `inferred` automatically; gate 1 resumes with operator edits and edits persist across a restart.

**Exit criteria — all met (offline + hosted validation):**
1. ✅ ≥ 8 facts extracted: pipeline produces exactly 8 facts from the fixture stub (all §17 facts present).
2. ✅ 100% of canon facts string-verify: `test_coverage_is_one_hundred_percent` passes; all 8 verbatim quotes from `fixtures.py` pass the §39.1 exact-match check against `vega_v1.html`.
3. ✅ Paraphrase/corruption demotes automatically: `test_paraphrase_quote_demotes_to_inferred` and `test_invented_claim_demotes_to_inferred` both pass — the verifier returns `verified=False`, builder sets `origin="inferred"`, no human intervention.
4. ✅ **Gate 1 edits persist across a restart** — validated on hosted Cloud Run deployment (GCP project `a2a-ghostrider-511215`):
   - Built Brain from source `src_3e90d98e70b8` (uploaded `vega_v1.html` to GCS bucket `vachan_bucket`).
   - Applied Gate 1 edit to fact `f_wading_depth` (changed `value` from "170 mm" to "180 mm").
   - Triggered full Cloud Run redeployment via Cloud Build.
   - Confirmed edit persisted — logs showed "Using Firestore backend (project=a2a-ghostrider-511215)" and the fact value remained "180 mm" across process restart.
   - Bug fixed during validation: added field validation to `apply_gate_ground()` to prevent silent failures when invalid field names are passed (valid: `{"value", "text", "origin", "predicate", "unit"}`).
5. ✅ **Gemini API integration operational (2026-10-11)**:
   - Model: `gemini-3.8-flash` (updated from deprecated `gemini-2.0-flash-001`)
   - API key configured in Cloud Run with service restriction (generativelanguage.googleapis.com only)
   - Extraction verified: 8 facts extracted with verbatim quotes, 3 entities (Product + 2 Places)
   - Structured output working with temperature=0, all quotes pass §39.1 verification
   - Detailed logging added to `extractor.py` showing full request/response cycle
   - Local validation via Docker Compose with mounted `.env` file

**Done / changed:**
- `backend/app/pipeline/extractor.py` — Gemini structured-output extraction (§37.1 schema, temperature=0) with offline stub fallback when `GEMINI_API_KEY` is unset. Stub uses verbatim quotes from `fixtures.py` so the verifier runs on real data even offline.
- `backend/app/services/verifier.py` — §39.1 mechanical verifier: NFC normalize → casefold → strip punctuation → exact substring → fuzzy token-set-ratio ≥ 95 (rapidfuzz) → demote. No model involved at any point.
- `backend/app/services/brain_store.py` — `_MemoryStore` (offline/tests) + `_FirestoreStore` (live) behind a factory. Auto-selects based on `GOOGLE_CLOUD_PROJECT` and `FIRESTORE_EMULATOR_HOST`.
- `backend/app/pipeline/brain_builder.py` — full pipeline: read source → extract → verify → assign fact IDs → persist entities/facts/spans → compute coverage → pause at gate 1 (`status=awaiting_gate`). `apply_gate_ground()` handles edits/drops/accepts and marks run `done`.
- `backend/app/models/brain.py` — expanded to all 8 stub facts; added `BrainRun`, `GateGroundPayload`, `FactEdit`, `BrainResult`; suppressed Pydantic `model_` namespace warning.
- `backend/app/fixtures.py` — 8 verbatim quote strings mapping `fact_id → quote` for the offline path.
- `backend/app/routers/brain.py` — `POST /v1/brain/build`, `GET /v1/brain/{source_id}`.
- `backend/app/routers/gates.py` — `POST /v1/gates/{run_id}/ground`, `GET /v1/gates/{run_id}/status`.
- `backend/app/config.py` — added `GEMINI_API_KEY`, `FIRESTORE_EMULATOR_HOST`, `extraction_model` settings.
- `backend/tests/test_verifier.py` — 14 verifier unit tests (all 8 exact matches, 2 fuzzy, 3 failure cases, coverage calc).
- `backend/tests/test_brain_pipeline.py` — 15 pipeline integration tests covering all 4 exit criteria + API endpoints.
- **39/39 tests pass** (up from 6 in T1).

**Couldn't do / shortcuts:**
- ✅ **GCP configuration complete** — `GOOGLE_CLOUD_PROJECT` and `GEMINI_API_KEY` configured in Cloud Run (2026-10-10/11); Firestore and Gemini operational.
- `POST /v1/brain/build` runs synchronously in the request (no Cloud Tasks queue yet). The plan calls for async jobs in P3+; P1 synchronous is sufficient for the demo flow and is noted as acceptable debt.

**Bugs found and fixed during implementation (logged per §6):**
- **Double `prod_` prefix**: `_entity_id_from_name` slug fallback was re-prefixing an already-prefixed subject string. Fixed by aligning the fallback slug logic with the extractor's `_entity_id()` function.
- **`offer_price` collision**: two facts sharing predicate `offer_price` (Mumbai + Bengaluru) overwrote each other in `_make_fact_id`. Fixed by value-fragment disambiguation in a `_KNOWN_WITH_VALUE` table checked before the predicate-only lookup.

**Alternative found:** none — implementation matched the plan.

**Blockers / follow-ups:**
- ✅ **All T2 validation complete (2026-10-10/11)** — GCP project `a2a-ghostrider-511215` operational; Firestore persistence validated across Cloud Run redeployment; Gemini extraction (`gemini-3.8-flash`) verified locally and on Cloud Run.
- Next task was **T3 — P2 Manifest schema freeze + linter** (completed).


### T3 — Manifest schema freeze + linter   ·   P2 / F16
- Status: DONE
- Dates: opened 2026-09-30 · updated 2026-09-30
- Goal: Freeze the manifest schema and ship a linter that exits non-zero on each invariant violated in isolation.

**Exit criteria — all met:**
1. ✅ Linter exits non-zero on each invariant violated — 33 tests, each mutates one field, asserts the expected INV-NN or SCHEMA code.
2. ✅ Golden manifest (`p0_single_beat.json`) lints clean — `python -m manifest_schema.linter fixtures/p0_single_beat.json --strict` exits 0.
3. ✅ Golden manifest renders in P0 player unchanged — `npx tsc --noEmit` clean, `npm run build` succeeds with identical hash.
4. ✅ Schema version pinned — `schema_version: "1.0"` enforced as a `const` in JSON Schema; any change is a SCHEMA violation.

**Done / changed:**
- `backend/manifest_schema/manifest.schema.json` — full §28 schema with all invariants as JSON Schema constraints (required fields, enum, pattern, minLength, const, minItems). Covers all beat/edge/slot/binding/vault/integrity fields.
- `backend/manifest_schema/linter.py` — standalone binary (`python -m manifest_schema.linter <file> [--strict]`). Three layers: (1) JSON Schema validation, (2) cross-reference checks (fact_ids → fact_index, vault_refs → vault, etc.), (3) semantic rules (kids_mode, locale declarations). 12 active invariants INV-01 through INV-14.
- `backend/tests/test_linter.py` — 33 tests: baseline (valid manifest + golden fixture lint clean), one per INV-NN, schema-level structural checks, binary exit codes (0/1/2), strict mode.
- `backend/requirements.txt` — added `jsonschema==4.23.0`.
- **72/72 tests pass** (39 from T2, 33 new).

**Couldn't do / shortcuts:** none — everything in the plan shipped.

**Alternative found:** none.

**Blockers / follow-ups:**
- ✅ **GCP setup complete; Gemini operational** (T1/T2 validated 2026-10-10/11)
- **Both builders can now work in parallel.** The manifest schema is the frozen interface; Builder A (backend) generates manifests, Builder B (frontend/runtime) consumes them. P3 (planner) is Backend-only. P4 (Vault) is Backend-only. **P5 (runtime + swap + embed) is Frontend-only and can start immediately** — it consumes the golden manifest and placeholder assets. P6 (transitions + scrubbing) needs P4's clips; P7 (claim guard) is Backend. The two-track parallelization starts now.
- **Audit correction, 2026-10-01:** `INV-14` was documented but implemented as a no-op, so a stating beat could have no facts. It now rejects that state, permits only explicit `mood: true` factless beats, and has isolated tests. This is a backward-compatible schema clarification, not a manifest-version change.
- **Audit correction, 2026-10-01:** Cloud Build now runs the strict golden-manifest linter after the backend suite, satisfying P2's every-push CI requirement.

### T4 — Planner, beats, slots, bindings, kids mode   ·   P3 / F6 F7 F8 F28 F29
- Status: DONE
- Dates: opened 2026-10-01 · updated 2026-10-01
- Goal: Turn approved, verified Vega V1 facts into a 7–10 beat manifest that passes the frozen P2 linter; enforce the P3 exit criteria in tests, including Gate 2 edits and kids-mode slot safety.

**Exit criteria — all met (offline):**
1. ✅ The approved fixture produces 8 beats (within the required 7–10) through the Vega ads adapter.
2. ✅ Every non-mood beat cites one or more verified `canon` facts; `b_hook` is explicitly `mood: true` with no fact IDs.
3. ✅ The planner-produced manifest passes the frozen P2 linter, including fact/span, reverse-index, Vault-reference, locale, and slot invariants.
4. ✅ A `kids_mode: true` build emits no non-sponsor slots (it currently emits no slots), asserted by test and linter.
5. ✅ `price` is registered as `offer.by_city` with a 300-second TTL; both city-specific `offer_price_*` canon facts remain in the manifest as the published-value fallback.
6. ✅ Gate 2 applies a constrained beat edit, re-lints, persists it, and moves the planner run to `done`.

**Done / changed:**
- `backend/app/pipeline/planner.py` — build-time planner: approved canon facts → 8-beat Vega ad manifest; fact-to-beat and fact-to-asset reverse indexes; planned P4 placeholder assets; price binding; kids-mode policy; frozen-schema lint gate; Gate 2 edit/re-lint/resume flow.
- `backend/app/routers/plans.py` — `POST /v1/plan/build` and `GET /v1/plan/{source_id}`. `backend/app/routers/gates.py` adds `POST /v1/gates/{run_id}/plan`; `manifest.py` can now serve a linted planned manifest by ID.
- `backend/app/models/brain.py` and `backend/app/services/brain_store.py` — persistent planner-run and manifest records for memory/Firestore backends.
- `backend/tests/test_planner.py` — 6 offline tests cover every P3 exit criterion plus planner/Gate 2/manifest API flow. **78/78 backend tests pass**.

**Couldn't do / shortcuts:** Live Gemini/Firestore execution remains unverified because `GEMINI_API_KEY` and GCP project configuration are still absent. Offline runs use the deterministic ads template, so all grounding, linting, and gate behavior is fully exercised without model credentials.

**Alternative found:** The ads adapter owns beat IDs, fact assignments, bindings, and integrity indexes; Gemini structured output is restricted to bilingual copy and is rejected if it changes those structural fields. This is a deliberate safety refinement: model output cannot weaken the fact-to-beat contract. No plan update required.

**Blockers / follow-ups:** P4 replaces `planned-p3` placeholder plates with content-addressed Vault assets. P5 can independently consume `m_<source_id>_standard` through `GET /v1/manifest/{manifest_id}`. Configure Gemini + GCP to exercise the live planner and Firestore persistence.

### T4.1 — Restore the golden manifest + fix `.gitignore`   ·   audit fix (P2)
- Status: DONE
- Dates: opened 2026-10-05 · updated 2026-10-05
- Goal: A fresh clone passes the full backend suite and the CI strict golden-lint step.

**What was wrong:** `.gitignore` carried a blanket `*.json` rule (with a few `!` exceptions). `backend/fixtures/p0_single_beat.json` — the P2 golden manifest that T1/T3 report as committed — was therefore **never in git**. On a clean tree, 4 tests failed (`test_manifest.py` ×3, `test_linter.py::test_golden_fixture_lints_clean`; 77/81 passed) and the Cloud Build `manifest_schema.linter fixtures/p0_single_beat.json --strict` step would fail. The same rule would also have silently dropped `frontend/package-lock.json`. This was an ignore-rule bug, not lost work: T1/T3 ran against a local copy.

**Done / changed:**
- `.gitignore` — replaced `*.json` with credential-only patterns (`service-account*.json`, `gcp-credentials*.json`, `*-key.json`, `*credentials*.json`). `.env` / `.env.*` remain ignored. No other JSON file became newly visible.
- `backend/fixtures/p0_single_beat.json` — recreated from the T1 description: one `b_flood` hold citing `f_wading_depth`, EN/HI text slots, `plate_flood_street` → `/assets/placeholder_flood_street.svg`, full integrity indexes, `coverage: 1.0`.
- Verified: strict linter exits 0; **81/81 backend tests pass**.

**Couldn't do / shortcuts:** The recreated fixture is not byte-identical to the original local file (its `span_id`/`brain_version` values are new placeholders). Nothing consumes those values beyond the linter and the P0 player.

**Alternative found:** Local dev works on **Python 3.12** (Homebrew `python@3.12`); the pinned wheels (`rapidfuzz`, `pydantic-core`) exist for 3.12. 3.14 fails to build `rapidfuzz`. The Dockerfile stays on 3.11. No plan update needed.

**Blockers / follow-ups:** `frontend/package-lock.json` will be committed with T5a's first `npm install`.

### T5a — Runtime, multi-beat playback, locale/city swap, bindings ladder   ·   P5 (part 1) / F17 F19 F8
- Status: DONE
- Dates: opened 2026-10-05 · GO 2026-10-05 · updated 2026-10-06
- Goal: The planner's 8-beat manifest plays end to end in a Remotion composition. Locale and city swap at play-time, `price` resolves through the §24.2 ladder, and the network log shows zero generation calls. Covers §64.7 criteria 1, 2 and 5; criteria 3–4 are T5b.

**Exit criteria — verified locally (backend :8080, Vite :5173, Playwright):**
1. ✅ **Variants render from one manifest.** `?variants=1` renders **48 variants** (12 cities × 2 locales × {standard, kids}); 24 from one manifest, the §76.3 two-locale number.
   - The 8 Mumbai/Bengaluru cells show rung 1, live.
   - The 40 cells for cities with no published price show rung-4 neutral wording. No price is invented.
2. ✅ **Zero generation calls.** The on-page network ledger, built from Resource Timing, lists only `GET /v1/manifest/*`, one plate GET (shared by all 48 variants) and `POST /v1/bindings/resolve`, so it reads **0 generation calls**. Video capture of this happens at P9 dry-run time.
3. ✅ **Resolver kill (criterion 5).** With `BINDINGS_FAIL=1` (503):
   - Bengaluru shows **₹1,27,400 "as published"**, badged to `offer_price_bengaluru`; the inspector shows the verbatim span "Bengaluru on-road ₹1,27,400".
   - Cities with no published fact show neutral wording.
   - Vitest asserts that every shown number is live or a cited canon fact.
4. ✅ **Mid-play swap.** Mumbai→Bengaluru rebinds ₹1,29,900→₹1,27,400, and EN→HI swaps the copy and the binding tags. The plate URL is unchanged, and there is no reload.

**Done / changed:**
- **Schema decision (both builders, in writing — user-approved 2026-10-05):** added an optional `integrity.facts: {fact_id: {value, unit, text, quote, origin}}`.
  - It is additive and backward-compatible, so the schema stays `1.0`.
  - Why it's needed: the frozen manifest had no fact values, so the §24.2 rung 3 ("as published") and the P7 inspector quote were impossible without the runtime reading the Brain (forbidden by §66).
  - New linter **INV-16**: when present, its keys equal `fact_index`, and every entry is `canon`.
  - The golden fixture carries it.
- **Planner:** emits `integrity.facts`. The quote is the **stored span text**, and the planner raises if a canon fact's span is missing (never paraphrase). The `b_offer` copy changed to the §18 script ("On-road in your city:" / "आपके शहर में:"), because the old "live when you play" contradicted the "as published" tag at rungs 2–4.
- **Backend:**
  - `routers/bindings.py`: `POST /v1/bindings/resolve`, with a config `live_offer_feed` (defaults equal the published prices). Unknown keys and cities are omitted, never guessed. Sends `Cache-Control: no-store`. `BINDINGS_FAIL=1` makes it return 503.
  - Tests: `tests/test_bindings.py` (4), plus 5 INV-16 linter tests and 1 planner test. **91/91 backend tests pass.**
- **Frontend:**
  - Added `remotion` and `@remotion/player` 4.0.533, and `vitest`.
  - `src/runtime/`:
    - `bindings.ts`: the pure `decideBinding` ladder, the C5 `BindingCache` keyed (resolver, city, sku), and the localised tags. TTL is aged by client receipt time; the server `resolved_at` goes on the receipt.
    - `composition.tsx` + CSS: §47 layers L0/L1 (Ken Burns)/L3/L4.
    - `timeline.ts`: shared timing constants.
    - `profile.ts`: `?profile=`, `?locale=`, `?city=`, `?entry_beat=`, and the 12-city set.
    - `useBindings.ts`: renders from the cache, revalidates every 15 s.
  - `BeatPlayer`: uses `<Player>`, adds a city selector and a rung readout, and drops the P0 debug strip.
  - `VariantGrid`: thumbnails plus the network ledger.
  - `api/client.ts`: `resolveBindings` with a 1.5 s timeout.
  - `useManifest`: fixed its pre-existing set-state-in-effect lint error.
  - **12/12 vitest**; `tsc`, `eslint` and `vite build` are clean.
  - `package-lock.json` is now committed (T4.1 follow-up).

**Couldn't do / shortcuts:**
- **Per-city plate swap** (§19 moment 6): still a schema gap, since there's no per-city plate field. Only the price rebinds. This is a both-builders decision before P4/T5b.
- **Parallax:** Ken Burns stands in for the depth parallax (T5b). There is no TTS selection yet: `audio_slots` are empty until P4.
- **Network evidence:** captured in-browser (the ledger and Playwright), not yet as a recorded video.
- **Remotion license:** we pass `acknowledgeRemotionLicense` on the assumption the team is 3 people or fewer, which is free under Remotion's license. Confirm team size before a public demo.

**Alternative found / issues logged:**
- **Manifest caching vs. mutable ids.** `GET /v1/manifest/{id}` sends `max-age=60`, but rebuilds reuse the same id (`m_<source>_standard`). During verification the browser served a stale manifest for up to 60 s. T5b must version manifest URLs (content hash) before moving to `immutable` (§49 C3).
- **Console warning (benign).** Chromium rejects `img.decode()` for the P0 SVG placeholder, so Remotion logs an `EncodingError` warning. It then falls back to `onload`, and the plate renders. This disappears with P4's raster plates.
- **Bundle size.** 173 kB gzipped, mostly Remotion. Watch it against T5b's < 2 s p95 first frame.
- **Local Python.** Use 3.12 locally (see T4.1).

**Blockers / follow-ups:** T5b (embed, Service Worker, degradation ladder, parallax, first-frame p95, versioned manifest URLs) is next to propose. To reproduce locally:
1. Run `uvicorn app.main:app --port 8080`.
2. `POST /v1/brain/build` with `{"source_id":"src_demo","gcs_path":"gs://vachan-vault/sources/src_demo/raw.html"}`. This falls back to the local fixture when GCS is down.
3. Pass Gate 1, run `/v1/plan/build` for standard and kids, and pass Gate 2.
4. Open `/?manifest=m_src_demo_standard&entry_beat=b_offer` or `&variants=1`.

### T5b — Embed, Service Worker, degradation ladder, parallax   ·   P5 (part 2) / F26 F11
- Status: DONE
- Dates: opened 2026-10-05 · GO 2026-10-06 · updated 2026-10-06
- Goal: §64.7 criteria 3–4.
  - The one-line embed renders inside a third-party page from a cold cache in < 10 s, with no host changes.
  - p95 first frame < 2 s.

**Exit criteria — verified locally:**
- **Setup:** `vite preview` production build on :4173, API on :8080, storefront on :8090. Playwright opened a fresh context for every run (cold: no HTTP cache, no SW).
- **What's measured:** host navigation → the embed's first frame with plate and text painted.

1. ✅ **Criterion 3 — embed under 10 s, cold.** `samples/storefront/index.html` is a static page on another origin, with only the pasted `<iframe>` and no host JS. The embed plays in it.
   - **Unthrottled:** p50 108 ms, p95 **121 ms** (n = 20).
   - **Emulated Fast 3G** (150 ms RTT, 1.6 Mbps): p95 **1.72 s** (n = 10).
2. ✅ **Criterion 4 — p95 first frame under 2 s.** **1.72 s** on Fast 3G, **0.12 s** unthrottled. All runs reached first frame via the depth-parallax path.
   - Caveat: this is localhost without a real CDN. Re-measure on the hosted URL when GCP exists (hosted register).
3. ✅ **Service Worker (C4).**
   - After the first visit, the bundles, plate, depth map and manifest are served by the SW. `POST /v1/bindings/resolve` is never cached.
   - **With the API killed**, a reload still plays all 8 beats from the cached manifest, and the price falls to ₹1,29,900 "as published" (rung 3, cited to its span).
4. ✅ **Degradation ladder.**
   - `?tier=still` gives a plain `<img>`, no motion. `still_parallax` and `full` give the WebGL depth canvas.
   - Pixel readback confirms the near layer moves (a window edge shifts 18→22 px) while the far layer holds.
   - Unit-tested: Save-Data, connection type, reduced motion, and no-WebGL → Ken Burns.
5. ✅ **Manifest freshness** (T5a issue). `no-cache` + a strong content `ETag` (sha256 of canonical JSON), with a 304 on `If-None-Match`. A rebuild is visible on the next play; an unchanged manifest costs a 304.

**Done / changed:**
- **Backend:**
  - `routers/manifest.py`: ETag, 304 and `Access-Control-Expose-Headers: ETag`.
  - `config.py`: CORS allows :4173 (preview).
  - `planner.py`: placeholder plates carry `depth_uri` → `/assets/placeholder_flood_street_depth.svg`, a hand-drawn depth map standing in for P4's monocular depth (§66.2 rule 3).
  - 2 new tests. **93/93 backend tests pass.**
- **Frontend:**
  - Two-page build (`index.html` + `embed.html`, via `build.rolldownOptions.input`).
  - `src/embed.tsx` + `EmbedApp`: chromeless, autoplay muted, quiet in-frame error.
  - `RuntimePlayer`: shared by the player page and the embed.
  - Runtime modules:
    - `runtime/tier.ts`: `chooseTier` + `renderPlan`.
    - `runtime/DepthParallax.tsx`: a WebGL displacement shader. The drift is a pure function of frame; it uses `delayRender` and falls back to Ken Burns.
    - `runtime/firstFrame.ts`: a User Timing mark, `window.__vachanFirstFrame`, and a `postMessage` to the parent.
    - `runtime/prefetch.ts`: preloads the entry beat and the next beat.
    - `runtime/embed.ts`: the snippet builder.
    - `runtime/serviceWorker.ts` + `public/sw.js`.
  - The player gets a "Copy embed" snippet panel.
  - Holds fall one rung on failure: parallax → Ken Burns, plate → gradient. The text layer is independent.
  - Players start on the entry beat's poster frame, so a paused player is never blank.
  - `firebase.json`: `sw.js` is `no-cache`. The page title is now "Vachan".
  - **24/24 vitest**; `tsc`, `eslint` and the build are clean.

**Couldn't do / shortcuts:**
- **Not browser-verified:**
  - The plate-load-failure → gradient path (Remotion `onError`). It needs a manifest with a broken plate URI; it's code-reviewed only.
  - Throttled `navigator.connection` → tier selection. CDP emulation doesn't drive `effectiveType`; it's covered by unit tests and `?tier=`.
- **SW cache never evicts old hashed bundles.** §51 calls for LRU eviction that never drops the current beat; deferred, since the demo has one build.
- **Low-res tier is untested on real assets.** It loads `poster_uri`, which equals the full plate until P4 produces real posters.
- **No recorded video** of the embed proof yet (P9 dry runs).

**Alternative found:** ETag revalidation instead of content-versioned manifest URLs. A pasted embed references a stable id and must survive rebuilds, so the "immutable per version" CDN rule (§49 C3) applies to Vault assets; the manifest is revalidated. No plan text changed; noted here.

**Blockers / follow-ups:**
- **P5 is complete locally.** Hosted re-measurement of criteria 3–4 is deferred with T1's hosting work.
- **Per-city plate variants** remain a both-builders schema decision.
- **Next candidates:**
  - **P6** client side: gesture scrubbing (needs clips from P4/P6-A, or placeholder clips).
  - **P7.5** play-log + receipt: B-side; the binding `{rung, source}` records from T5a feed it directly.
  - **P4** Vault, once Gemini/GCP credentials exist.

### T6 — Play-log + receipt   ·   P7.5 / F23
- Status: DONE
- Dates: opened 2026-10-06 · GO 2026-10-06 (user: "do the next tasks") · updated 2026-10-06
- Goal: §64.10 exit criteria:
  1. The record matches what was on screen: claims, price shown, locale, refusal count.
  2. The signature verifies.
  3. The chain verifies across three consecutive plays.
  4. Tampering with any one field fails verification (a test).

**Exit criteria — all met:**
1. ✅ **The record is what was on screen.**
   - The player appends a segment whenever the visible screen changes: beat, locale, city, badged claims, binding display/rung/provenance.
   - In the browser, one play recorded b_offer en/Mumbai → en/Bengaluru → hi/Bengaluru → b_warranty. Each segment carries its claims, price and provenance; the receipt shows refusals 0 (P7 adds them).
   - The server **refuses to sign** a screen the manifest can't produce (7 parametrised cases), a stale manifest version (409), and unknown fields such as a PII-carrying `viewer_email` (422).
2. ✅ **The signature verifies.** HMAC-SHA256 over canonical JSON, checked via the API and in the receipt ("✓ verifies").
3. ✅ **The chain verifies.** Three consecutive plays chain (test); in the browser, "✓ 4 plays chained", later 6 including embed flushes. Dropping or editing a stored record breaks the chain at that record and the next.
4. ✅ **Tampering fails.** It is parametrised over 10 fields: price shown, rung, claim, locale, refusal count, beat order, manifest version, seq, prev_hash, signature. The receipt's "Try tampering" edits a copy and shows "✓ altered copy rejected".

**Done / changed:**
- **Backend:**
  - `services/playlog.py`: record schema (`extra=forbid`), canonical JSON, sign/verify, `seal`, `validate_against_manifest`, `verify_chain`.
  - Brain store: `append_play` is atomic (a lock in memory, a Firestore transaction on `playlog_heads/{manifest_id}`), plus `get_play` and `get_plays_by_manifest`.
  - `routers/playlog.py`: `POST /v1/playlog` (accepts `text/plain` for keepalive), `POST /v1/playlog/verify`, `GET /v1/playlog/chain/{manifest_id}`, `GET /v1/playlog/{play_id}`.
  - `routers/manifest.py`: `load_manifest()` factored out, so signing validates against exactly what the player is served.
  - `config.playlog_hmac_key`. Local dev uses an ephemeral key; any other environment returns 503 rather than sign with no key.
  - 28 new tests. **121/121 backend tests pass.**
- **Frontend:**
  - `runtime/claims.ts`: shared "what is badged" logic, so the badges and the receipt can't disagree.
  - `runtime/playlog.ts`: `PlayRecorder`, segments, `profileHash` (coarse profile, no PII).
  - `runtime/usePlayLog.ts`: page-hide keepalive flush; `submit()` starts the next play.
  - `RuntimePlayer.onBeatChange`: from Remotion `frameupdate`/`seeked`.
  - `useManifest` returns the ETag `version`. The client gets `submitPlay`, `verifyPlay` and `fetchChain`.
  - `Receipt` + CSS. The player gets "End play & view receipt"; the embed logs plays on page hide.
  - **29/29 vitest**; `tsc`, `eslint` and the build are clean.

**Bug found and fixed during verification:** the first browser run lost every screen before a locale/city swap. The recorder was keyed on the profile hash, which includes locale and city, so each swap started a new play. Now there's one recorder per manifest version, and the hash is pinned from the profile the play started with. A regression test covers it.

**Couldn't do / shortcuts:**
- **Firestore path not run.** The transactional append is written but untested (no Firestore/emulator, same as T2).
- **Questions/refusals are empty until P7.** The guard will append `{type}` refusals; the fields are already signed.
- **Live prices are attested as received.** Rung 1/2 values are checked for resolver and shape; the server doesn't re-query the feed at signing time.

**Alternative found / observations:**
- **Flicker on load and city swap.** The live price arrives a few hundred ms after first paint, so the screen briefly shows the published fact (rung 3) before the live value (rung 1). The receipt records both, faithfully. That's the ladder's "never wait on the network" rule. Possible UX refinement: hold the price for ≤300 ms while a first fetch is in flight. Logged; not changed.
- **Navigation flushes too.** Leaving the player page flushes its in-progress play, so a viewer who opens the embed after the player leaves two records. Correct per "every play leaves a receipt".

**Blockers / follow-ups:** T7 (P6 client gesture scrubbing) is next. P7 (guard) needs Gemini credentials for its primary path.

### T7 — Transition edges + gesture scrubbing (no Veo)   ·   P6 / F13 F14 F18
- Status: DONE (clips are placeholders; Veo swap pending credentials)
- Dates: opened 2026-10-06 · GO 2026-10-06 (user: "do the next tasks") · updated 2026-10-06
- Goal: §64.8 criteria, using **placeholder clips**: Veo needs credentials, so the clip *source* is a deterministic camera move over the placeholder plate, but the encoding, checks and runtime are the real ones.

**Exit criteria:**
1. ✅ **≥ 2 clips.** `clip_flood_to_spec` (3.0 s, 72 frames) and `clip_range_to_offer` (2.5 s, 60 frames), 260 KB and 196 KB.
2. ✅ **Every frame `pict_type=I`, zero B.** `tests/test_encode.py` runs in CI (Cloud Build installs `requirements-dev.txt`, which now includes `imageio-ffmpeg`). The checker is itself tested: it **fails** an ordinary GOP encode.
3. ✅ **`duration_s × fps == frame_count`.** Asserted for both clips.
4. ✅ **Drag scrubs forward and backward.**
   - Real pointer drag in Chromium: clip time 0.23 → 1.23 s going up, 0.97 → 0.50 s coming back.
   - Seek latency (432 frame-step seeks): **all-intra p95 2.6 ms, backward p95 2.6 ms**, vs **7.9 ms** for the same clip as a normal GOP (2 I / 38 P / 32 B). That's well inside the 16.7 ms budget for 60 fps.
   - ⚠️ Still to check by hand: "60 fps on the demo laptop" with a real finger/trackpad. Headless measurements can't prove frame pacing.
5. ✅ **Release before 0.8 scrubs back without committing.** It returns to `b_flood` at the frame the viewer left, with the playhead and play state restored. Past 0.8 it commits into `b_spec_overlay`.
6. ✅ **No seam at either join.**
   - Measured: frame 0 vs hold A's plate is **52.9 / 54.0 dB PSNR**; last frame vs hold B's derived plate is **47.0 / 49.2 dB** (test threshold 35 dB).
   - The runtime side is exact by design: holds now start and end on their **hinge frame** (motion envelope `sin(π·t)`, 0 at both ends; unit-tested), so a hold's last frame is the raw plate.
   - Not frame-by-frame eyeballed at the join on the demo laptop yet.

**Schema decision (user-approved 2026-10-06):** optional, additive `beat.branch_only`; schema stays 1.0.
- **INV-17:** every branch_only beat is an edge target.
- **INV-18:** every non-empty `edge.clip` is a vault clip asset.

**Done / changed:**
- **Backend:**
  - `pipeline/encode.py`: all-intra encoder (`-g 1 -bf 0`), plus a `frame_types` / `verify_all_intra` checker built on showinfo (no ffprobe needed), `join_psnr` and `extract_frame`.
  - `pipeline/placeholder_clips.py`: two recipes; clips are conditioned on hold A's plate, and hold B's plate is **derived from the clip's last frame** (§39.3).
    - Content-addressed: one changed recipe re-encoded only that clip, a rerun encodes **0**, and superseded files are pruned.
    - The registry is `placeholder_vault.json`.
  - Planner: the placeholder plate is now a raster PNG (rendered once from the SVG); adds `b_spec_overlay` (branch_only; wading, clearance, charge) and edges `e_flood_spec` (drag_up, reversible) and `e_range_offer` (click), with clip assets and derived target plates.
  - Linter: INV-17 and INV-18.
  - **133/133 backend tests pass.**
- **Frontend:**
  - `runtime/path.ts`: spine (non-branch beats + auto-edge clips), `branchPath`, timeline, segment lookup, `posterFrame`.
  - `runtime/scrub.ts`: drag→progress, edge frame, commit at 0.8, easing.
  - `timeline.ts`: hinge-neutral `holdMotion`, Ken Burns and parallax offsets. `DepthParallax` takes an overscan uniform.
  - The composition plays the path: an `EdgeClip` (`Html5Video`) whose source copy fades over the first quarter, which becomes a cut to the target plate below `low` tier or under reduced motion. Branch beats render a spec panel of published facts.
  - `RuntimePlayer`: affordance pills (§58); drag-up scrub with pointer capture; hover-preview (600 ms) / leave / click-commit; restore on cancel.
  - **38/38 vitest**; `tsc`, `eslint` and the build are clean.

**Bug found and fixed during verification:** a hover preview unmounted its own pill. The ease animation seeked before React rendered the branched path, and the frame listener, holding a stale timeline, mapped the frame to the wrong segment and moved the hold index. With the pill gone, `pointerleave` never fired and the preview stuck at the clip end. Fixes:
- Frame mapping reads the latest timeline from a ref.
- The hold index is frozen while a gesture is in flight.
- Gesture seeks wait for a `ready` flag set when the branched path's pending seek lands.

A click is also marked `committing`, so a quick pointer-leave can't cancel it.

**Couldn't do / shortcuts:**
- **Clips are placeholders**, not Veo (§37.3): an ffmpeg camera move, with no product consistency to judge. The swap changes bytes only; ids, edges and the derived-plate rule stay.
- **Mid-hold jump:** a drag starting mid-hold jumps from the hold's current pose (≤ 6 % zoom / ≤ 2 % drift) to the clip's hinge frame. Endpoint joins are exact.
- **Reverse edge not built:** there's no drag-down from the spec sheet back to the flood beat. `reversible` is in the manifest, unused.
- **Branch stays in the path:** a committed branch stays in the path across loops.
- **Unlabelled badges:** the spec panel's three badges don't say which fact each one is.

**Follow-ups:**
- When Veo exists: replace `placeholder_clips` recipes with the image-conditioned generator, keeping encode/verify/derive.
- The Cloud Run encode job's image will need ffmpeg (apt). The API image doesn't encode.
- Remaining build order: **P7** (claim guard, needs Gemini), **P4** (Vault, needs Gemini Image/TTS), **P8** accessibility, **P9** evals/deck. The next credential-free item is P8 (captions/audio-description track); P7 has a planned keyword-rules fallback (§32.1 #11) but its primary path needs Gemini.
