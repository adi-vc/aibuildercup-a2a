# Handoff — where Vachan stands (2026-10-06)

This is a snapshot for whoever picks the build up next. It summarises the work; [`PLAN_TRACKER.md`](PLAN_TRACKER.md) has the full per-task detail: every exit criterion, its measurements, the shortcuts taken and the bugs fixed. The workflow in [`AGENTS.md`](AGENTS.md) §6 still applies: propose the task, mark it `GO`, work on one task at a time, and log as you go.

## TL;DR

- **Built locally:** P0–P3, P5, P6 (with placeholder clips) and P7.5. That covers the swap, the embed, the drag-to-scrub branch and the signed receipt — about **39 of the 75 live demo seconds** (slides 7b, 10–12).
- **Blocked on credentials:** P4 (Vault) and P7 (claim guard — the refusal moment, slides 8–9). There is still no `GEMINI_API_KEY` and no GCP project.
- **Never hosted:** everything runs on localhost with in-memory storage. The hosted proofs are `DEFERRED`; see "Hosted validation" below.
- **Tests:** 133 backend (pytest) and 38 frontend (vitest), all green. `tsc`, `eslint`, `vite build` and the strict golden-manifest lint are all clean.

## Phase status

| Phase | Task | Status | Notes |
|---|---|---|---|
| P0 walking skeleton | T1 | ✅ local · ⏸ hosted | Deploy config exists; project IDs are placeholders. |
| P1 Brain + span verifier | T2 | ✅ offline · ⏸ Firestore | Uses stub extraction when there's no Gemini key; the verifier is real. |
| P2 schema + linter | T3, T4.1 | ✅ | T4.1 restored the golden fixture, which `.gitignore` had silently excluded. |
| P3 planner | T4 | ✅ | Deterministic ads template; Gemini only rewrites copy. |
| **P4 Vault** | — | ❌ **not started** | Needs Gemini Image, TTS and depth. Placeholders stand in (see below). |
| P5 runtime, swap, embed | T5a, T5b | ✅ local | Cold first-frame p95: 0.12 s unthrottled, 1.72 s on Fast 3G. |
| P6 edges + scrubbing | T7 | ✅ placeholder clips | All-intra verified in CI; the real Veo clips come later. |
| **P7 claim guard** | — | ❌ **not started** | Needs Gemini Flash. A keyword-rule fallback exists in the plan (§32.1 #11). |
| P7.5 play-log + receipt | T6 | ✅ local | HMAC signing and per-manifest chain; Firestore path written but never run. |
| P8 accessibility | — | ❌ | High-contrast skin is doable now; captions and audio description need P4 TTS. |
| P9 adapters, evals, deck | — | ❌ | |
| D13 second ad product | — | ❌ | Optional; build only after the hero works smoothly. |

## Run it locally

Use **Python 3.12**. 3.14 can't build `rapidfuzz`, and 3.11 matches the Dockerfile. Use Node 24.

```bash
# backend
cd backend
python3.12 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/uvicorn app.main:app --port 8080            # in-memory store, offline stubs

# frontend (second terminal)
cd frontend && npm ci && npm run dev                  # http://localhost:5173

# tests
cd backend && .venv/bin/python -m pytest -q           # ~80 s; GCS timeouts fall back to the fixture
cd frontend && npm test && npm run lint && npm run build
```

**Build a demo manifest.** The store is in-memory, so repeat this after every API restart:

```bash
curl -s -X POST localhost:8080/v1/brain/build -H 'content-type: application/json' \
  -d '{"source_id":"src_demo","gcs_path":"gs://vachan-vault/sources/src_demo/raw.html"}'   # → run_id
curl -s -X POST localhost:8080/v1/gates/<run_id>/ground -H 'content-type: application/json' -d '{}'
curl -s -X POST localhost:8080/v1/plan/build -H 'content-type: application/json' -d '{"source_id":"src_demo"}'   # → plan run_id
curl -s -X POST localhost:8080/v1/gates/<plan_run_id>/plan -H 'content-type: application/json' -d '{}'
# repeat the plan/build + gates/plan pair with "kids_mode":true for m_src_demo_kids
```

**Demo URLs** (all on `http://localhost:5173`):

| URL | What it shows |
|---|---|
| `/?manifest=m_src_demo_standard` | The full player, with locale/city swap, a "Copy embed" button and "End play & view receipt". |
| `&entry_beat=b_offer` | Opens on the price beat. Also try `b_flood` (the drag-up pill) and `b_range` (the click pill). |
| `&variants=1` | 48-variant grid with a network ledger showing 0 generation calls. |
| `&tier=still` (or `low`, `still_parallax`) | Forces a rung of the degradation ladder. |
| `/embed.html?manifest=m_src_demo_standard&city=mumbai&locale=en-IN` | The chromeless embed. |
| `samples/storefront/index.html` | A dummy third-party page. Serve it on another port with `python3 -m http.server 8090 --directory samples/storefront`. Its iframe points at `vite preview` on `:4173`. |

**Environment variables.** No `.env.example` exists yet; worth adding one.

| Variable | Effect |
|---|---|
| `GEMINI_API_KEY` | Enables live extraction and planner copy. Offline stubs are used without it. |
| `GOOGLE_CLOUD_PROJECT` / `FIRESTORE_EMULATOR_HOST` | Switches the store from memory to Firestore. |
| `PLAYLOG_HMAC_KEY` | Play-log signing key; inject it from Secret Manager in production. Locally a per-process ephemeral key is used; non-local environments refuse to sign without one. |
| `BINDINGS_FAIL=1` | Kills the price resolver, to demo the §24.2 fallback ladder. |
| `VITE_API_BASE_URL` | Frontend → API base. Defaults to `http://localhost:8080`. |

## What was built in this session (T4.1 → T7)

- **T4.1:** `.gitignore`'s blanket `*.json` rule had kept the golden fixture and `package-lock.json` out of git. The rule now names credential files only.
- **T5a, P5 runtime:**
  - The Remotion composition, which implements the §47 layers.
  - Mid-play locale/city swap.
  - The §24.2 binding ladder (live → stale → cited published fact → neutral), served by `POST /v1/bindings/resolve`.
  - The variant grid and network ledger.
- **T5b, P5 embed:**
  - The one-line `<iframe>` embed and a Service Worker cache. With the API down, a reload still plays from cache and falls back to the published price.
  - Manifests are served `no-cache` with an ETag, so a rebuild shows up on the next play.
  - The degradation ladder and a WebGL depth-parallax layer.
- **T6, P7.5:**
  - The player records a segment for each screen change. The server validates it against the manifest, then signs it (HMAC-SHA256 over canonical JSON) and chains it (`seq` + `prev_hash`).
  - A receipt view with signature, chain and tamper checks.
- **T7, P6:**
  - An all-intra encoder and verifier (`backend/app/pipeline/encode.py`).
  - Content-addressed placeholder clips (`placeholder_clips.py`). Each clip starts on hold A's plate, and hold B's plate is derived from the clip's last frame.
  - The runtime plays a path of holds and edges. Drag-up scrubs, release past 0.8 commits, and click edges preview on hover.

## Contract changes made (all additive; schema stays `1.0`, each approved in writing)

1. `integrity.facts` maps `fact_id → {value, unit, text, quote, origin}`, so the runtime can show "as published" values and source quotes without reading the Brain. Linter rule **INV-16**.
2. `beat.branch_only` marks beats reached only by an edge (e.g. `b_spec_overlay`). Linter rules **INV-17** (reachable) and **INV-18** (an edge's clip is a vault clip).
3. Also changed in the planner:
   - The placeholder plate is now a raster `placeholder_flood_street.png`, with a hand-drawn depth map.
   - `b_offer` copy now follows §18 ("On-road in your city:").
   - Two edges were added: `e_flood_spec` (drag up) and `e_range_offer` (click).

## What remains

### Needs credentials (highest demo value first)

1. **P7 claim guard:** `/v1/ask` and the refusal UI, slides 8–9, the most memorable mechanism.
   - Needs `GEMINI_API_KEY`.
   - The play-log already has signed `questions` and `refusals` fields, so the guard only has to append to them.
2. **P4 Vault:**
   - Bible, plates (Gemini Image), the no-baked-text vision check, depth maps, patches, TTS with SSML marks, and gate 3.
   - Real assets replace the placeholders with no runtime change; plates, depth and clips are referenced by vault URI.
3. **Veo clips (the A-side of P6):** replace the recipes in `placeholder_clips.py` with image-conditioned Veo generation. Keep `encode_all_intra`, `verify_all_intra` and the derive-last-frame rule.

### Credential-free

- **Studio review screens (slide 6, 13 live seconds).** The gate 1 API (`POST /v1/gates/{run_id}/ground`) and gate 2 API exist, but there is no studio UI: no facts shown beside highlighted spans, no accept/edit/drop. `frontend/` has only the player, embed, variant grid and receipt.
- **P8:** high-contrast skin.
- **P7 fallback:** the keyword-rules version (§32.1 #11) if Gemini stays unavailable.
- **`.env.example`** and a checked-in `scripts/build_demo_manifests.sh` wrapping the curl sequence above.
- **P9 evals:** the `evals/report.py` harness. First-frame, variant-count and seek-latency numbers already exist in the tracker as starting data.

### Open decisions

- **Per-city plates** (§19 moment 6). The schema has no field for them, so only the price swaps by city. This needs a both-builders schema decision.
- **Third locale** (§76.3) decides metric 3: 24 vs 36 variants. The grid currently shows 48: 12 cities × 2 locales × {standard, kids}.
- **Remotion license:** confirm the team is ≤ 3 people, or buy a company license. The code passes `acknowledgeRemotionLicense`.

### Hosted validation (deferred; follow `docs/HOSTED_VALIDATION_RUNBOOK.md`)

- **T1:** the deployed URL opens from another device. **T2:** a Gate 1 edit survives an API restart on Firestore.
- **T5b:** re-measure the embed cold-load and first-frame p95 on the real CDN.
- **T6:** exercise the Firestore transactional chain append.

### Known gaps and polish (details in the tracker)

- The price briefly shows "as published" before the live value lands, on first load and after a city swap. That's correct per the ladder; it could hold for ≤ 300 ms.
- A drag that starts mid-hold jumps from the current zoom to the clip's hinge frame. Endpoint joins are exact.
- The reverse edge (drag down from the spec sheet) isn't built. A committed branch stays in the path across loops.
- The Service Worker never evicts old hashed bundles.
- The spec panel's three badges are unlabelled.
- "60 fps on the demo laptop" and a frame-by-frame seam check need a human on real hardware.

## Where things live

| Area | Files |
|---|---|
| Binding ladder | `frontend/src/runtime/bindings.ts` |
| Composition + layers | `frontend/src/runtime/composition.tsx`, `timeline.ts`, `DepthParallax.tsx` |
| Paths + gestures | `frontend/src/runtime/path.ts`, `scrub.ts`, `frontend/src/components/RuntimePlayer.tsx` |
| Degradation, SW, embed | `frontend/src/runtime/tier.ts`, `frontend/public/sw.js`, `frontend/embed.html`, `src/components/EmbedApp.tsx` |
| Play-log | `frontend/src/runtime/playlog.ts`, `usePlayLog.ts`, `src/components/Receipt.tsx` · `backend/app/services/playlog.py`, `app/routers/playlog.py` |
| Encoding + clips | `backend/app/pipeline/encode.py`, `placeholder_clips.py`, `placeholder_vault.json`, `frontend/public/assets/vault/` |
| Contract | `backend/manifest_schema/manifest.schema.json`, `linter.py` (INV-01 … INV-18) |
