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

| Task | Status | Environment | Remaining hosted proof |
|---|---|---|---|
| T1 · P0 walking skeleton | `DEFERRED` | Shared GCP / Firebase Hosting | External device/network opens the deployed frontend; source upload reaches shared GCS. |
| T2 · P1 Brain persistence | `DEFERRED` | Firestore emulator or shared Firestore | A Gate 1 edit survives a complete API-process restart. |

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

**Nothing in flight.** T4 is `DONE`. P4 (Vault) or P5 (runtime + swap + embed) may be proposed next; the two tracks remain independent behind the frozen manifest schema.

## Task log

### T1 — Walking skeleton   ·   P0 / F1◐ F17◐
- Status: DEFERRED
- Dates: opened 2026-09-30 · updated 2026-10-01
- Goal: Prove the whole pipe end-to-end with minimal content, deployed to real infrastructure.

**Exit criteria — criteria 1–2 are met locally; hosted criterion 3 is deferred:**
1. ✅ `POST /v1/sources/upload` accepts the fixture HTML, snapshots it to GCS (emulated locally via fake-gcs-server), returns a `source_id` + 3 stub facts.
2. ✅ The `p0_single_beat` manifest renders in a browser at `http://localhost:5173` — dark city-street SVG with "30 cm of water. Still going." overlaid as a text layer. Switching locale dropdown to `hi-IN` swaps the text without changing the image (text-is-a-layer proven in P0).
3. ⚠️ **Awaiting GCP project setup.** All deploy config is in place (`cloudbuild.yaml`, `cloudrun-service.yaml`, `frontend/.firebaserc`) but `YOUR_FIREBASE_PROJECT_ID` / `YOUR_PROJECT_ID` / `YOUR_REGION` are still placeholders. A teammate fills those in and runs `gcloud builds submit` to complete criterion 3.

**Done / changed:**
- `backend/` — FastAPI app (`main.py`, `config.py`), Pydantic models (`models/brain.py`), routers (`sources.py`, `manifest.py`), GCS service (`services/storage.py`), 6 passing tests, `Dockerfile` (multi-stage, Python 3.11-slim, non-root), `requirements.txt`.
- `backend/fixtures/` — `vega_v1.html` (authoritative Vega V1 source with all 8 §17 facts as verbatim spans; refusal-driving gaps deliberately absent) + `p0_single_beat.json` (hand-written single-beat manifest, `schema_version: "1.0"`, integrity indexes populated).
- `frontend/` — React 19 + Vite 8 + TypeScript. `src/types/manifest.ts` mirrors §28 schema. `BeatPlayer` component: plate, text layer, locale selector, fact badges (click → shows `fact_id`, `span_id`, `origin: canon`). `useManifest` hook. Vite proxy `/v1` → `localhost:8080`. `tsc --noEmit` clean; `npm run build` succeeds (224 kB bundle).
- `frontend/public/assets/placeholder_flood_street.svg` — dark city-street-in-rain SVG standing in for a real Vault plate.
- Root: `docker-compose.yml` (fake-gcs-server + API hot-reload), `models.yaml` (pinned model versions), `.gitignore`, `cloudbuild.yaml` (6-step CI/CD), `cloudrun-service.yaml`, `SKELETON.md`, `backend/README.md`, `frontend/README.md`.

**Couldn't do / shortcuts:**
- Exit criterion 3 (deployed URL accessible to a teammate) requires a GCP project and Firebase project. Config is scaffolded but not filled in. This is the expected state for P0 on a fresh repo — fill in the project IDs and run `gcloud builds submit`.
- No real GCS bucket used locally; the docker-compose emulator (`fake-gcs-server`) is sufficient for P0. The storage service is emulator-aware and will switch to real GCS once `GCS_EMULATOR_HOST` is unset and ADC is configured.

**Alternative found:**
- **Python 3.11 required (not 3.9).** `google-cloud-storage` pulls in `cryptography`, which needs pre-built wheels. macOS system Python 3.9 lacks them; Python 3.11 ships them. The Dockerfile uses `python:3.11-slim` to match. Not a debt — 3.11 is the correct choice — but noted here so teammates don't hit the same wheel-build failure. **No plan update needed** (the plan is model/tool-agnostic and doesn't pin a Python version).

**Blockers / follow-ups:**
- To fully satisfy exit criterion 3: fill in `frontend/.firebaserc`, `cloudrun-service.yaml`, and `cloudbuild.yaml` substitutions with real GCP/Firebase project IDs, then run `gcloud builds submit`.
- **Deferred hosted validation:** This does not block later build phases. Follow [`docs/HOSTED_VALIDATION_RUNBOOK.md`](docs/HOSTED_VALIDATION_RUNBOOK.md) when a GCP/Firebase project is available, then restore `DONE` only after an external device opens the deployed frontend.
- Next task: **T2 — P1 Brain + span verification** (`vachan-plan.md` §64.3). This wires real Gemini extraction + the §39.1 mechanical span verifier, replacing the 3 stub facts in `brain.py`.

### T2 — Brain + span verification   ·   P1 / F2 F3 F29◐
- Status: DEFERRED
- Dates: opened 2026-09-30 · updated 2026-10-01
- Goal: Wire real Gemini extraction + mechanical §39.1 span verifier + Firestore persistence. Exit criteria per §64.3: ≥8 facts extracted from fixture; 100% of canon facts string-verify; a deliberately corrupted fact demotes to `inferred` automatically; gate 1 resumes with operator edits and edits persist across a restart.

**Exit criteria — criteria 1–3 are met offline; Firestore-backed restart validation for criterion 4 is deferred:**
1. ✅ ≥ 8 facts extracted: pipeline produces exactly 8 facts from the fixture stub (all §17 facts present).
2. ✅ 100% of canon facts string-verify: `test_coverage_is_one_hundred_percent` passes; all 8 verbatim quotes from `fixtures.py` pass the §39.1 exact-match check against `vega_v1.html`.
3. ✅ Paraphrase/corruption demotes automatically: `test_paraphrase_quote_demotes_to_inferred` and `test_invented_claim_demotes_to_inferred` both pass — the verifier returns `verified=False`, builder sets `origin="inferred"`, no human intervention.
4. ⚠️ Gate 1 edits persist during the in-memory process (`test_gate1_edit_persists`, `test_gate1_drop_removes_fact`, and `test_gate1_edits_persist_across_store_reads` pass), but true process-restart persistence is not demonstrated until Firestore/emulator is configured.

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
- ⚠️ **GCP project IDs still placeholder** — Firestore and live Gemini calls require `GOOGLE_CLOUD_PROJECT` and `GEMINI_API_KEY` in `.env`. Set these to run against real infrastructure; the offline stub path covers all tests without them.
- `POST /v1/brain/build` runs synchronously in the request (no Cloud Tasks queue yet). The plan calls for async jobs in P3+; P1 synchronous is sufficient for the demo flow and is noted as acceptable debt.

**Bugs found and fixed during implementation (logged per §6):**
- **Double `prod_` prefix**: `_entity_id_from_name` slug fallback was re-prefixing an already-prefixed subject string. Fixed by aligning the fallback slug logic with the extractor's `_entity_id()` function.
- **`offer_price` collision**: two facts sharing predicate `offer_price` (Mumbai + Bengaluru) overwrote each other in `_make_fact_id`. Fixed by value-fragment disambiguation in a `_KNOWN_WITH_VALUE` table checked before the predicate-only lookup.

**Alternative found:** none — implementation matched the plan.

**Blockers / follow-ups:**
- Set `GEMINI_API_KEY` + `GOOGLE_CLOUD_PROJECT` in `.env` (and optionally `FIRESTORE_EMULATOR_HOST`) to exercise the live Gemini path against the real fixture URL.
- **Audit correction, 2026-10-01:** the old “restart” test re-read the same in-memory store and therefore could not prove persistence across a process restart. Run the Gate 1 edit flow against Firestore or its emulator, then restart the API before restoring `DONE`.
- **Deferred hosted validation:** This does not block later build phases. Follow [`docs/HOSTED_VALIDATION_RUNBOOK.md`](docs/HOSTED_VALIDATION_RUNBOOK.md) when Firestore/emulator infrastructure is available, then restore `DONE` after the persisted edit is read by a new API process.
- Next task: **T3 — P2 Manifest schema freeze + linter** (`vachan-plan.md` §64.4). This is the gate everything passes through — both builders align on the schema before parallel work begins.

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
- ⚠️ **GCP/Gemini keys still pending** — carried forward from T1/T2.
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
