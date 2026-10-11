# T9 Quick Start — Asset Curation in 3 Hours

**Goal:** Replace placeholder assets with real curated media for the demo.

## Checklist

### Phase 1: Setup (5 min)
- [ ] Verify GCS access: `gsutil ls gs://vachan_bucket`
- [ ] Check directories exist: `ls app/pipeline/vault_staging/`
- [ ] Test upload script: `./scripts/upload_vault_assets.sh dry-run`

### Phase 2: Curate Plates (60-90 min)
- [ ] Generate 6 plates via Gemini Playground / ImageFX:
  - [ ] `b_hook` — Dramatic reveal
  - [ ] `b_flood` — Flooded street
  - [ ] `b_spec_overlay` — Dashboard/tech
  - [ ] `b_warranty` — Battery closeup
  - [ ] `b_range` — Highway/journey
  - [ ] `b_offer` — Showroom/lifestyle
- [ ] Convert to WebP: `cwebp -q 85 input.png -o plate_NAME.webp`
- [ ] Save to `app/pipeline/vault_staging/plates/`
- [ ] **Check:** No baked text (numbers, letters) in any plate

### Phase 3: Generate Depth Maps (30-45 min)
- [ ] For each plate, generate depth map:
  - **Option A:** Upload to [MiDaS web demo](https://huggingface.co/spaces/pytorch/MiDaS)
  - **Option B:** Hand-draw in Photoshop (white=far, black=near)
- [ ] Match dimensions to source plate (1920×1080)
- [ ] Save to `app/pipeline/vault_staging/depth/` with matching names
- [ ] **Check:** Grayscale PNG, full range (0-255)

### Phase 4: Generate Audio (30-45 min)
- [ ] English (en-IN) phrases:
  ```bash
  gcloud tts synthesize-speech \
    --text="170 millimeters of wading depth. Still going." \
    --language-code=en-IN \
    --voice=en-IN-Neural2-A \
    --output=vault_staging/audio/en-IN/wading_depth.mp3
  ```
  - [ ] Hook tagline
  - [ ] Wading depth
  - [ ] Clearance
  - [ ] Charge time
  - [ ] Range
  - [ ] Warranty
  - [ ] Offer
- [ ] Hindi (hi-IN) equivalents (use Google Translate + native speaker review)
- [ ] Save to `vault_staging/audio/{locale}/`
- [ ] **Check:** Audio plays, natural pacing

### Phase 5: Create Badges (20-30 min)
- [ ] Create 3-5 badge SVGs in Figma/Canva:
  - [ ] Warranty badge (shield icon)
  - [ ] Specs badge (gear icon)
  - [ ] Price badge (tag icon)
- [ ] Export as SVG or PNG @2x (transparent background)
- [ ] Save to `vault_staging/patches/`
- [ ] **Check:** No text in badges (text comes from text_slots)

### Phase 6: Upload to Vault (10 min)
- [ ] Dry run: `./scripts/upload_vault_assets.sh dry-run`
- [ ] Review output (file count, GCS URIs)
- [ ] Real upload: `./scripts/upload_vault_assets.sh`
- [ ] Verify: `gsutil ls -r gs://vachan_bucket/vault/`
- [ ] **Check:** All assets uploaded with `immutable` cache headers

### Phase 7: Update Planner (20 min)
- [ ] Note uploaded GCS URIs from upload script output
- [ ] Edit `app/pipeline/planner.py`:
  - Map `b_hook` → `gs://vachan_bucket/vault/plates/plate_hook_HASH.webp`
  - Map `b_flood` → `gs://vachan_bucket/vault/plates/plate_flood_HASH.webp`
  - (Repeat for all 6 beats)
- [ ] Update `VAULT_PLATES` dict in planner
- [ ] Update `VAULT_DEPTH` dict
- [ ] (Optional) Update `audio_uri` in text_slots

### Phase 8: Test (15 min)
- [ ] Rebuild manifest:
  ```bash
  curl -X POST localhost:8080/v1/plan/build \
    -H 'content-type: application/json' \
    -d '{"source_id":"src_demo"}'
  ```
- [ ] Open player: `http://localhost:5173/?manifest=m_src_demo_standard`
- [ ] **Check:**
  - [ ] Real plates load (not placeholders)
  - [ ] Depth parallax works with real depth maps
  - [ ] No console errors for missing assets
  - [ ] Looks polished and on-brand

### Phase 9: Document (10 min)
- [ ] Update `PLAN_TRACKER.md` T9 with:
  - Asset count (plates, depth, audio, patches)
  - Upload evidence (GCS URIs)
  - Any shortcuts taken
  - Known issues
- [ ] Mark T9 status: `IN PROGRESS` → `DONE`

---

## Time Budget

| Phase | Optimistic | Realistic | Pessimistic |
|---|---|---|---|
| Setup | 5 min | 10 min | 20 min |
| Plates | 60 min | 90 min | 120 min |
| Depth maps | 30 min | 45 min | 60 min |
| Audio | 30 min | 45 min | 60 min |
| Badges | 20 min | 30 min | 40 min |
| Upload | 10 min | 15 min | 30 min |
| Planner update | 20 min | 30 min | 45 min |
| Test | 15 min | 20 min | 30 min |
| Document | 10 min | 15 min | 20 min |
| **Total** | **3h 20min** | **4h 40min** | **6h 5min** |

**Plan for 4-5 hours** with breaks.

---

## Shortcuts (If Time Is Short)

1. **Use stock photos** instead of generating plates (saves 60 min)
2. **Skip depth maps** — Ken Burns fallback works without them (saves 45 min)
3. **Reuse T7 placeholder clips** — they work perfectly (saves 0 min, already done)
4. **Skip badges** — text-only layers work (saves 30 min)
5. **English-only audio** — defer Hindi to post-demo (saves 30 min)

**Minimum viable:** 6 plates + skip everything else = **~90 min**.

---

## Troubleshooting

### "Gemini Playground is slow"
→ Use ImageFX or stock photos (Pexels, Unsplash)

### "MiDaS web demo not loading"
→ Hand-draw depth maps in Photoshop (5 min per plate)

### "gcloud tts command not found"
→ Install Cloud SDK: `brew install --cask google-cloud-sdk`

### "Upload script fails"
→ Check credentials: `gcloud auth application-default login`

### "Player shows 404 for assets"
→ Check GCS URIs in planner match uploaded filenames exactly

---

## Success Criteria

✅ **At least 6 real plates** replace placeholders  
✅ **Depth parallax works** (or Ken Burns fallback is acceptable)  
✅ **No baked text** in any plate  
✅ **Brand-consistent** look (silver/blue palette)  
✅ **Player loads smoothly** with no console errors  

**When these pass:** T9 is `DONE`. Move to P8 (accessibility) or P9 (evals).

---

## Resources

- **Full guide:** `ASSET_CURATION_GUIDE.md`
- **Pipeline docs:** `app/pipeline/README.md`
- **Scaffold code:** `app/pipeline/{bible,image_gen,depth,vision_check,tts,vault_uploader}.py`
- **Upload script:** `scripts/upload_vault_assets.sh`
- **Registry:** `app/pipeline/vault_registry.json`

**Next task after T9:** P8 accessibility or P9 evals.
