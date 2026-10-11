# Asset Curation Guide — T9 Hackathon Approach

This guide shows how to curate Vault assets manually using UI tools, for **faster, cheaper, better-looking demo results** than full automated generation.

## Overview

T9 uses a **hackathon-optimized workflow:**
- **Pipeline scaffold code** (in `app/pipeline/`) proves the architecture
- **Manual curation** via UI tools produces demo-ready assets
- **Upload script** uploads to GCS vault with content-addressing
- **Planner updates** emit vault URIs instead of placeholder paths

---

## 1. Plates (6 images minimum)

### What you need
6 plates matching the Vega V1 ad beats:
1. `b_hook` — Dramatic reveal/hero shot
2. `b_flood` — Vehicle in flooded street (wading depth)
3. `b_spec_overlay` — Tech specs / dashboard closeup
4. `b_warranty` — Battery / warranty visual
5. `b_range` — Highway / long road (efficiency concept)
6. `b_offer` — Showroom / lifestyle (price beat)

### Generation options

**Option A: Gemini Playground** (recommended, free)
1. Go to [ai.google.dev/gemini-api/prompts/image_generation](https://ai.google.dev/gemini-api/prompts/image_generation)
2. Use consistent brand prompts (see below)
3. Generate 2-3 variants per beat
4. Download best results as PNG/JPEG
5. Convert to WebP: `cwebp -q 85 input.png -o plate_flood_001.webp`

**Option B: ImageFX** (Google's image tool)
1. Go to [aitestkitchen.withgoogle.com/tools/image-fx](https://aitestkitchen.withgoogle.com/tools/image-fx)
2. Same prompts, download results

**Option C: Stock photos** (free, fastest)
1. Search Pexels, Unsplash, Pixabay for:
   - "electric car flooded street"
   - "SUV dashboard technology"
   - "car showroom modern"
2. Download high-res (1920×1080 min)
3. Crop to 16:9 if needed

### Brand-consistent prompts

```
b_hook (hero reveal):
"Sleek silver electric SUV on dramatic mountain road at golden hour, cinematic lighting, 
premium automotive photography, 8K, wide angle, atmospheric"

b_flood (wading depth proof):
"Silver electric SUV driving through deep flooded urban street, water splashing dramatically,
rain, dramatic lighting, photorealistic, action shot"

b_spec_overlay (tech focus):
"Modern electric SUV interior dashboard closeup, futuristic display screens, 
blue ambient lighting, high-tech, clean, product photography"

b_warranty (battery confidence):
"Electric vehicle battery pack technical closeup, industrial aesthetic, clean, 
modern factory, quality engineering, blue and silver tones"

b_range (efficiency):
"Electric SUV on open highway, long empty road stretching to horizon, 
sunset sky, wide landscape, sense of journey, cinematic"

b_offer (lifestyle/showroom):
"Premium electric SUV in modern showroom, warm lighting, welcoming atmosphere,
lifestyle photography, professional, inviting"
```

**Key consistency rules:**
- Always include "electric SUV" or "electric vehicle"
- Keep color palette: silver/grey vehicle, blue accents
- Avoid baked text (numbers, letters, UI elements)
- Use "photorealistic" or "product photography" for quality
- Aspect ratio: 16:9 (1920×1080 ideal)

### File naming convention

```
plate_<beat>_<hash>.webp

Examples:
- plate_flood_a8f3c2.webp
- plate_hook_d9e1f4.webp
- plate_offer_c4b7a9.webp
```

The hash can be random (6 hex chars) for manually curated assets. The upload script will compute real SHA-256 hashes.

### Save to:
```
backend/app/pipeline/vault_staging/plates/plate_*.webp
```

---

## 2. Depth Maps (6, matching plates)

### What you need
One depth map per plate (same dimensions, grayscale PNG).

### Generation options

**Option A: MiDaS web demo** (easiest)
1. Go to [huggingface.co/spaces/pytorch/MiDaS](https://huggingface.co/spaces/pytorch/MiDaS) (or similar hosted demo)
2. Upload your plate image
3. Download the depth map (grayscale PNG)
4. Rename to match plate: `depth_flood_a8f3c2.png`

**Option B: DepthAnything online**
1. Search for "DepthAnything online demo" or "monocular depth estimation online"
2. Upload plate, download depth map

**Option C: Hand-draw in Photoshop/GIMP** (full control)
1. Create new grayscale layer same size as plate
2. Paint white = far (sky, background)
3. Paint black = near (vehicle, foreground objects)
4. Use soft brush for smooth transitions
5. Export as PNG

### Depth map rules
- **Grayscale only** (RGB will work but wastes space)
- **Same dimensions** as source plate (1920×1080)
- **Full range:** use near-black (0-50) and near-white (200-255)
- **Smooth gradients:** avoid hard edges unless object boundaries

### File naming:
```
depth_<beat>_<hash>.png

Must match the plate hash:
- plate_flood_a8f3c2.webp → depth_flood_a8f3c2.png
```

### Save to:
```
backend/app/pipeline/vault_staging/depth/depth_*.png
```

---

## 3. Audio (TTS, 2 locales)

### What you need
~8 phrases per locale (en-IN, hi-IN):
- Hook tagline
- Wading depth
- Clearance, charge time, range (3 phrases)
- Warranty
- Offer/price

### Generation options

**Option A: Google Cloud TTS console** (free tier, good quality)
```bash
# English (en-IN)
gcloud tts synthesize-speech \
  --text="170 millimeters of wading depth. Still going." \
  --language-code=en-IN \
  --voice=en-IN-Neural2-A \
  --output=vault_staging/audio/en-IN/wading_depth.mp3

# Hindi (hi-IN)
gcloud tts synthesize-speech \
  --text="170 मिलीमीटर की जलमग्नता गहराई। अभी भी चल रहा है।" \
  --language-code=hi-IN \
  --voice=hi-IN-Neural2-A \
  --output=vault_staging/audio/hi-IN/wading_depth.mp3
```

**Option B: ElevenLabs** (premium, paid)
1. Sign up at elevenlabs.io
2. Choose Indian English voice
3. Paste phrases, generate, download MP3
4. Repeat for Hindi (use transliteration or native speaker script)

**Option C: Cloud TTS web console**
1. Go to [cloud.google.com/text-to-speech](https://cloud.google.com/text-to-speech)
2. Use "Try it" panel
3. Select language: en-IN or hi-IN
4. Choose Neural2 voice
5. Enter text, listen, download

### Phrase list (Vega V1)

**English (en-IN):**
```
hook: "Built for roads that break others."
wading: "170 millimeters of wading depth. Still going."
clearance: "80 centimeters of ground clearance."
charge: "50-minute fast charge to 80 percent."
range: "500 plus kilometers certified range."
warranty: "8-year battery warranty."
offer: "On-road in your city."
```

**Hindi (hi-IN):** *(Use native speaker or Google Translate, then verify)*
```
hook: "उन सड़कों के लिए बनाया गया जो दूसरों को तोड़ देती हैं।"
wading: "170 मिलीमीटर की जलमग्नता गहराई। अभी भी चल रहा है।"
clearance: "80 सेंटीमीटर की ग्राउंड क्लीयरेंस।"
charge: "50 मिनट में 80 प्रतिशत तक फास्ट चार्ज।"
range: "500 प्लस किलोमीटर प्रमाणित रेंज।"
warranty: "8 साल की बैटरी वारंटी।"
offer: "आपके शहर में ऑन-रोड।"
```

### File naming:
```
audio/<locale>/<phrase_id>.mp3

Examples:
- audio/en-IN/wading_depth.mp3
- audio/hi-IN/wading_depth.mp3
```

### Save to:
```
backend/app/pipeline/vault_staging/audio/en-IN/*.mp3
backend/app/pipeline/vault_staging/audio/hi-IN/*.mp3
```

---

## 4. Patches (Badges/Buttons)

### What you need
3-5 badge SVGs or PNGs:
- Warranty badge
- Specs badge
- Price/offer badge
- (Optional: "Ask ❓" button)

### Generation options

**Option A: Figma** (best quality)
1. Create 100×100px frame
2. Draw badge shape (circle, rounded rect, shield)
3. Add icon (warranty = shield, specs = gear, price = tag)
4. Export as SVG or PNG @2x

**Option B: Canva** (easiest)
1. Search "badge template" or "icon"
2. Customize colors (match brand: blue/silver)
3. Remove text (we add text via text_slots)
4. Download as PNG (transparent background)

**Option C: Inkscape** (free vector editor)
1. Create badge shapes
2. Export as SVG

### Badge specs
- **Size:** 100×100px (or 200×200 @2x)
- **Format:** SVG preferred (scalable), PNG acceptable
- **Transparency:** yes (alpha channel)
- **Colors:** match brand (blue #3B82F6, silver #94A3B8)
- **No text:** badges are just shapes/icons; copy comes from text_slots

### File naming:
```
patch_<type>.svg or patch_<type>.png

Examples:
- patch_warranty_badge.svg
- patch_specs_badge.svg
- patch_price_badge.png
```

### Save to:
```
backend/app/pipeline/vault_staging/patches/patch_*.svg
backend/app/pipeline/vault_staging/patches/patch_*.png
```

---

## 5. Transition Clips (Optional)

### Can we reuse T7 placeholders?
**Yes!** The existing clips work:
- `clip_flood_to_spec.mp4` (3.0s, 72 frames, all-intra)
- `clip_range_to_offer.mp4` (2.5s, 60 frames, all-intra)

They're encoded correctly, gesture scrubbing works, and joins are seamless.

### If you want real clips:

**Option A: Stock video** (easiest)
1. Search Pexels Video, Pixabay for:
   - "car driving transition"
   - "urban street to highway"
   - "dashboard closeup"
2. Download 1920×1080 MP4
3. Trim to 2-4 seconds
4. Re-encode all-intra:
```bash
ffmpeg -i input.mp4 -c:v libx264 -g 1 -bf 0 -crf 18 \
  -an -r 24 -s 1920x1080 clip_custom.mp4
```

**Option B: Keep placeholders**
No action needed. The clips work.

### Save to (if generating custom):
```
backend/app/pipeline/vault_staging/clips/clip_*.mp4
```

---

## 6. Upload to GCS Vault

Once assets are curated and saved to `vault_staging/`, upload them:

### Dry run (preview):
```bash
cd backend
./scripts/upload_vault_assets.sh dry-run
```

### Real upload:
```bash
./scripts/upload_vault_assets.sh
```

This will:
- Compute SHA-256 hashes for each file
- Upload to `gs://vachan_bucket/vault/<type>/`
- Set immutable cache headers (`max-age=31536000`)
- Print GCS URIs for each asset

### Verify upload:
```bash
gsutil ls -r gs://vachan_bucket/vault/
```

---

## 7. Update Planner to Emit Vault URIs

After upload, update `app/pipeline/planner.py` to reference real vault URIs instead of placeholder paths:

```python
# Before (placeholder):
"plate_uri": "/assets/placeholder_flood_street.png"

# After (vault):
"plate_uri": "https://storage.googleapis.com/vachan_bucket/vault/plates/plate_flood_a8f3c2.webp"
```

Map beat IDs to uploaded asset URIs:

```python
VAULT_PLATES = {
    "b_hook": "https://storage.googleapis.com/.../plate_hook_d9e1f4.webp",
    "b_flood": "https://storage.googleapis.com/.../plate_flood_a8f3c2.webp",
    "b_spec_overlay": "https://storage.googleapis.com/.../plate_spec_c8a7f3.webp",
    # ...
}

VAULT_DEPTH = {
    "b_hook": "https://storage.googleapis.com/.../depth_hook_d9e1f4.png",
    # ...
}
```

---

## 8. Test End-to-End

After uploading and updating the planner:

```bash
# Rebuild manifest with vault URIs
curl -X POST localhost:8080/v1/plan/build -H 'content-type: application/json' \
  -d '{"source_id":"src_demo"}'

# View in player
open http://localhost:5173/?manifest=m_src_demo_standard
```

**Expected:**
- Real plates load (not placeholders)
- Depth parallax works with real depth maps
- Audio plays (if audio_uri is set in text_slots)
- Badges display (if patch URIs are set)

---

## Cost Estimate

| Asset Type | Count | Unit Cost | Total |
|---|---|---|---|
| Plates (Gemini Playground) | 6 | Free tier | $0 |
| Depth maps (MiDaS web demo) | 6 | Free | $0 |
| TTS (Cloud TTS) | 16 phrases | ~$0.03 | ~$0.50 |
| Patches (Figma/Canva) | 3-5 | Free | $0 |
| Clips (stock or reuse) | 0-2 | Free | $0 |
| **Total** | | | **< $1** |

If using ElevenLabs TTS (premium): ~$5 for 16 phrases.

---

## Troubleshooting

### "No baked text" — how to verify?
1. Open plate in image viewer
2. Zoom to 100%
3. Look for any letters, numbers, UI elements
4. If found, regenerate with prompt: "no text, no numbers, clean image"

### Depth map doesn't work?
1. Check dimensions match plate exactly
2. Verify it's grayscale (not RGB)
3. Check file extension is `.png`
4. Ensure full range (0-255) is used

### Audio sounds robotic?
1. Use Neural2 voices (better quality)
2. Add SSML pauses: `<break time="300ms"/>`
3. Adjust speaking rate: `<prosody rate="95%">...</prosody>`
4. Try ElevenLabs if budget allows

### Upload fails?
1. Check `gsutil` is installed: `gsutil --version`
2. Authenticate: `gcloud auth application-default login`
3. Verify bucket access: `gsutil ls gs://vachan_bucket`

---

## Next Steps After Curation

1. ✅ Assets curated and saved to `vault_staging/`
2. ✅ Upload script runs successfully
3. ✅ Vault registry updated with asset metadata
4. ⏳ Update planner to emit vault URIs
5. ⏳ Test manifest with real assets
6. ⏳ Record video proof (P9) showing real plates vs placeholders

**Timeline:** 2-4 hours for full curation (6 plates + 6 depth + 16 audio + 3 patches).

---

**Questions?** Check `app/pipeline/*.py` for scaffolds showing production patterns, or review `PLAN_TRACKER.md` T9 entry for exit criteria.
