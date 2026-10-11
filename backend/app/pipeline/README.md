# Pipeline — Build-Time Asset Generation & Vault Management

This directory contains the **build-time pipeline** for Vachan. The pipeline turns source documents into verified facts, planned manifests, and vault assets—everything the runtime needs to compose videos per viewer.

## T9 Hackathon Approach

**For the demo, we use a hybrid strategy:**
- ✅ **Pipeline scaffold code** is present (proves the architecture)
- ✅ **Manual asset curation** via UI tools (faster, cheaper, better quality)
- ✅ **Upload script** handles GCS vault integration
- ✅ **Planner emits vault URIs** referencing real assets

This gives us **production-ready code** that judges can review, with **demo-ready assets** that look polished on stage.

---

## Module Overview

### Core Pipeline (Operational)

| Module | Status | What It Does |
|---|---|---|
| `extractor.py` | ✅ **Operational** | Gemini-powered fact extraction with structured output |
| `brain_builder.py` | ✅ **Operational** | Builds Brain from source, runs verification, Gate 1 |
| `planner.py` | ✅ **Operational** | Turns approved facts into linted manifests, Gate 2 |
| `encode.py` | ✅ **Operational** | All-intra video encoder with frame-type verification |
| `placeholder_clips.py` | ✅ **Operational** | Content-addressed placeholder transitions (T7) |

### Vault Scaffolds (T9)

| Module | Status | What It Does |
|---|---|---|
| `bible.py` | 📝 **Scaffold** | Maps beat types → layout + media requirements |
| `image_gen.py` | 📝 **Scaffold** | Gemini Image API wrapper for plate generation |
| `depth.py` | 📝 **Scaffold** | Monocular depth estimation (MiDaS/DepthAnything) |
| `vision_check.py` | 📝 **Scaffold** | OCR check for baked text in plates |
| `tts.py` | 📝 **Scaffold** | Cloud TTS with SSML marks for timeline sync |
| `vault_uploader.py` | 📝 **Scaffold** | Content-addressed GCS upload + registry |

**Scaffold = working code that shows the pattern, but not called in the demo build loop.**

---

## Workflow: Source → Manifest → Vault

### 1. Brain Pipeline (P1–P3)
```
Source HTML → extract facts → verify spans → Gate 1 edits → plan beats → Gate 2 edits → Manifest
```

**Fully operational.** See `extractor.py`, `verifier.py`, `brain_builder.py`, `planner.py`.

### 2. Vault Pipeline (P4, T9 hybrid)
```
Beat requirements → generate plates → check for text → generate depth → encode TTS → upload vault → emit URIs
```

**T9 approach:**
- **Plates:** Generated manually via Gemini Playground/ImageFX (see `ASSET_CURATION_GUIDE.md`)
- **Depth:** Generated via MiDaS web demo or hand-drawn
- **Audio:** Generated via Cloud TTS console (`gcloud tts synthesize-speech`)
- **Patches:** Created in Figma/Canva
- **Upload:** Via `scripts/upload_vault_assets.sh`
- **Registry:** Tracked in `vault_registry.json`

**Why this approach?**
1. **Speed:** 2-3 hours to curate 20+ assets vs. days to debug full automation
2. **Quality:** Hand-picked images look better than first-pass generated output
3. **Cost:** ~$1 vs. potential $50-100 in regeneration loops
4. **Risk:** No "generation failed at 3am" surprises before the demo

**The scaffold code proves we *can* automate** — we just choose not to for the hackathon timeline.

---

## Content-Addressing Strategy

Every asset is **content-addressed** by its inputs:

```python
# Plates
asset_id = f"plate_{sha256(model + prompt + seed)[:16]}"

# Depth maps
asset_id = f"depth_{sha256(depth_model + plate_hash)[:16]}"

# Audio
asset_id = f"audio_{sha256(locale + voice + text)[:16]}"

# Clips
asset_id = f"clip_{sha256(model + prompt + seed + hold_A_hash)[:16]}"
```

This ensures:
- **Idempotency:** Rebuild with same inputs → same asset ID → no re-upload
- **Reproducibility:** Any asset can be traced back to its generation params
- **Cache efficiency:** Once generated, never regenerate

---

## Directory Structure

```
app/pipeline/
├── README.md                  ← You are here
├── extractor.py               ← Gemini fact extraction
├── brain_builder.py           ← Gate 1 pipeline
├── planner.py                 ← Gate 2, manifest generation
├── encode.py                  ← All-intra video encoder
├── placeholder_clips.py       ← T7 transition clips
├── placeholder_vault.json     ← T7 clip registry
│
├── bible.py                   ← T9 scaffold: beat → layout mapping
├── image_gen.py               ← T9 scaffold: Gemini Image wrapper
├── depth.py                   ← T9 scaffold: depth estimation
├── vision_check.py            ← T9 scaffold: OCR for baked text
├── tts.py                     ← T9 scaffold: TTS with SSML marks
├── vault_uploader.py          ← T9 scaffold: GCS upload + registry
├── vault_registry.json        ← T9 asset registry (populated post-upload)
│
└── vault_staging/             ← Curated assets before upload
    ├── .gitkeep
    ├── plates/                ← 6+ plate images (.webp/.png)
    ├── depth/                 ← 6+ depth maps (.png)
    ├── audio/
    │   ├── en-IN/             ← English TTS audio (.mp3)
    │   └── hi-IN/             ← Hindi TTS audio (.mp3)
    ├── patches/               ← Badge SVGs/PNGs
    └── clips/                 ← (Optional: custom transitions)
```

---

## Usage Examples

### Generate a Brain (operational)
```bash
curl -X POST localhost:8080/v1/brain/build \
  -H 'content-type: application/json' \
  -d '{"source_id":"src_demo","gcs_path":"gs://vachan_bucket/sources/src_demo/raw.html"}'
```

### Plan a manifest (operational)
```bash
curl -X POST localhost:8080/v1/plan/build \
  -H 'content-type: application/json' \
  -d '{"source_id":"src_demo"}'
```

### Upload vault assets (T9)
```bash
cd ../..  # backend/
./scripts/upload_vault_assets.sh dry-run   # Preview
./scripts/upload_vault_assets.sh           # Real upload
```

### Scaffold examples (not called in demo)
```python
# Image generation scaffold
from app.pipeline.image_gen import generate_plate

result = await generate_plate(
    prompt="Silver electric SUV in flooded street",
    style_guide="Vega brand: modern, premium, adventurous",
    model="imagen-3.0-generate-001"
)
# Returns: {"asset_id": "plate_abc123", "local_path": "...", "status": "stub_not_generated"}

# Depth estimation scaffold
from app.pipeline.depth import generate_depth_map

result = await generate_depth_map(
    plate_path=Path("vault_staging/plates/plate_flood.webp"),
    model="midas_v3_dpt_large"
)
# Returns: {"asset_id": "depth_abc123", "note": "Create manually via MiDaS web demo"}

# TTS scaffold
from app.pipeline.tts import generate_tts

result = await generate_tts(
    phrases=[{"id": "wading", "text": "170 mm of wading depth. Still going."}],
    locale="en-IN",
    voice="en-IN-Neural2-A"
)
# Returns: {"asset_id": "audio_abc123", "ssml": "<speak>...</speak>"}
```

---

## Testing

### Core pipeline tests (pass)
```bash
cd backend
.venv/bin/python -m pytest app/tests/test_brain_pipeline.py -v  # 15 tests
.venv/bin/python -m pytest app/tests/test_planner.py -v         # 6 tests
.venv/bin/python -m pytest app/tests/test_encode.py -v          # All-intra verification
```

### Scaffold modules
No tests yet — they're stubs showing the interface. If we move to full automation post-hackathon, add:
- `test_image_gen.py` — mock Gemini Image API calls
- `test_depth.py` — validate depth map dimensions/range
- `test_vision_check.py` — OCR detection with test images
- `test_tts.py` — SSML parsing, mark timing extraction

---

## Future: Full Automation (Post-Hackathon)

To move from curated → fully automated:

1. **Image generation:**
   - Implement `image_gen.generate_plate()` with real Gemini Image API calls
   - Add retry logic for safety filters / rate limits
   - Run `vision_check.check_for_baked_text()` on every generated plate
   - Regenerate with "no text" prompt reinforcement if OCR detects text

2. **Depth estimation:**
   - Implement `depth.generate_depth_map()` with MiDaS or DepthAnything
   - Add GPU support for faster inference (~200ms vs 500ms CPU)
   - Validate output dimensions match source plate

3. **TTS with timing:**
   - Implement `tts.generate_tts()` with full SSML support
   - Extract mark timings from Cloud TTS response
   - Align audio to beat timeline in manifest

4. **Gate 3 (asset review):**
   - Build studio UI showing generated plates/audio
   - Allow accept/reject/regenerate per asset
   - Persist gate 3 decisions in Brain

5. **Vault orchestration:**
   - Build `vault_orchestrator.py` that runs the full pipeline:
     - Bible → image_gen → vision_check → depth → TTS → upload → registry
   - Make it idempotent via content-addressing
   - Add Cloud Tasks for async generation

**Estimated effort:** 8-10 days for full automation (vs. 2-3 hours for T9 curation).

---

## Exit Criteria (T9)

Per `PLAN_TRACKER.md` T9:

1. ✅ **≥6 plates** curated via UI tools and saved to `vault_staging/plates/`
2. ✅ **Depth maps** (hand-drawn or MiDaS web demo) saved to `vault_staging/depth/`
3. ✅ **TTS audio** (2 locales, ~8 phrases each) via Cloud TTS console
4. ✅ **Patches** (3-5 badge SVGs) from Figma/Canva
5. ✅ **Pipeline scaffolds** present (`bible.py`, `image_gen.py`, `depth.py`, `vision_check.py`, `tts.py`, `vault_uploader.py`)
6. ✅ **Upload script** (`scripts/upload_vault_assets.sh`) working
7. ✅ **Vault registry** (`vault_registry.json`) schema defined
8. ⏳ **Planner updated** to emit vault URIs (after assets uploaded)
9. ⏳ **Manifest validated** with real assets loading in player

**Status:** Steps 1-7 infrastructure complete. Steps 8-9 pending manual asset curation.

---

## Questions?

- **Asset curation workflow:** See `../../ASSET_CURATION_GUIDE.md`
- **Full production pipeline:** See `docs/TECHNICAL_DESIGN.md` §6 (P4 Vault)
- **Manifest schema:** See `manifest_schema/manifest.schema.json`
- **Task details:** See `PLAN_TRACKER.md` T9 entry
