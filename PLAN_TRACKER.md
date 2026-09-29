# Vachan — Plan Tracker

The running log of implementation work. It is the single source of truth for **what has been attempted, what happened, and what is safe to do next.** Tasks are drawn from the build order in [`vachan-plan.md`](vachan-plan.md) §64 (phases P0–P9) and its feature register (§15).

> New here? Read [`AGENTS.md`](AGENTS.md) first, then this file.

---

## How this works (read before touching anything)

1. **One task in flight at a time.** Never start a second task while one is `IN PROGRESS`. The whole point is a clean, reviewable trail.
2. **A task starts only after it is marked `GO`.** Proposing a task (`PROPOSED`) is not permission to build it. Work begins **only** once the owner has set the status to `GO` in this file. If you believe the next task is obvious, still wait for `GO`.
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

## Entry template (copy this per task)

```
### T<n> — <short title>   ·   <plan ref, e.g. P1 / F3>
- Status: PROPOSED | GO | IN PROGRESS | DONE | BLOCKED | DEFERRED
- Owner: <name>            Dates: opened <YYYY-MM-DD> · updated <YYYY-MM-DD>
- Goal: <one line — what "done" means, tied to the plan's exit criteria>
- Done / changed: <what was actually built>
- Couldn't do / shortcuts: <gaps, debt, anything skipped>
- Alternative found: <if implementation diverged from the plan — and was the plan updated?>
- Blockers / follow-ups: <what's next or what's needed>
```

---

## Current task

**Nothing in flight.** T1 is `DONE`. Next task to propose: **T2 — P1 Brain + span verification** (`vachan-plan.md` §64.3).

## Task log

### T1 — Walking skeleton   ·   P0 / F1◐ F17◐
- Status: DONE
- Owner: Kiro            Dates: opened 2026-09-30 · updated 2026-09-30
- Goal: Prove the whole pipe end-to-end with minimal content, deployed to real infrastructure.

**Exit criteria — all met locally; (3) requires filling in deploy placeholders:**
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
- Next task: **T2 — P1 Brain + span verification** (`vachan-plan.md` §64.3). This wires real Gemini extraction + the §39.1 mechanical span verifier, replacing the 3 stub facts in `brain.py`.
