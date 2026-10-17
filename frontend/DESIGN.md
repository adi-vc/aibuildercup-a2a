# Vachan design system

How the frontend looks and why. Values live in [`src/styles/tokens.css`](src/styles/tokens.css); the chapter system in [`src/styles/base.css`](src/styles/base.css). Change them there, never inline.

## Direction: colour chapters

The player page is a row of full-bleed posters, one flat colour field per chapter, held together by one typeface and one grid. The page tells the pitch in order:

| Chapter | Field | What it holds |
|---|---|---|
| **Watch** | ultramarine over black | the ad, composed for this viewer |
| **Sources** | taxi yellow | every figure the ad states, with the span it was verified against |
| **Ask** | ultramarine | the claim guard, inline: answers from the source, or refusals |
| **Receipt** | green | the signed record of exactly what this viewer saw |
| **Embed** | black | one line of HTML, then the colophon |

**The idea:** the 30 cm waterline becomes the seam between two colour fields. In Watch, the video sits across the seam: half in the monsoon sky, half "under water".

**The colours are the subject's own:**
- ultramarine is the monsoon sky;
- black and yellow are Mumbai's kaali-peeli taxis;
- **green is the one accent**, used for actions and "verified", never larger than a button.

The direction, palette and type were dealt by taste-skill (`draw.mjs`, direction `colour-chapters`, seed 1440003606) and adapted for a stage demo (see `PLAN_TRACKER.md` T10.1).

## Rules

The house style, measured by taste-skill's inspector.

- **Type:**
  - One face, Jost, self-hosted (`@fontsource`, no CDN, so the embed cold start stays fast), with Noto Sans Devanagari for Hindi.
  - Display is bold capitals, tight (−0.03em, leading 0.9).
  - Text is 400/500 at 16px or more. Five steps: `--step-small / body / lead / head / display`.
  - Banned: Inter, Roboto, Arial, Open Sans, Helvetica; monospace outside real code.
- **Surfaces:**
  - Flat fields and one-step tone changes (`--step-*`).
  - **No** 1px outlined boxes, hairline dividers, glass/backdrop blur, gradients, or shadows on things at rest.
  - The only gradient is the neutral scrim under copy on the video.
  - Real tables keep their rules.
  - Interface fragments marked `data-ui` (the receipt card) keep their own card conventions.
- **Shape:** square corners and square buttons everywhere on the page (`--radius: 0`).
- **Copy:**
  - Sentence case at reading size: no eyebrows, no tiny tracked labels, no emoji, no index numbers.
  - Headlines are two lines or fewer at every width.
- **Pictures:**
  - Real, credited photographs of the ad's world (monsoon Mumbai, its taxis, old Bangalore), one per chapter at most, square-cropped flat on the field.
  - None is presented as the product.
  - Credits are in the colophon and in `public/assets/world/credits.json`.
- **Motion:**
  - The fixed header takes the colour of the chapter beneath it (`useChapters`).
  - Chapter parts rise in once, staggered.
  - Buttons press to `scale(0.97)`.
  - Photos drift slowly.
  - Everything stops under `prefers-reduced-motion`, and content only hides once script runs (`.js`).

## Two coordinate systems

1. **The page** (`App.css`, `components/*.module.css`) is in CSS pixels.
2. **The video's layers** (`runtime/composition.module.css`) are in composition pixels (1280×720), scaled by the Remotion Player.
   - Copy is a bold capital lower third; the live price is taxi yellow; provenance sits on flat solid tiles.
   - `--controls-clearance` lifts the copy above the player's control bar.
   - On phones (≤600px) the overlay controls are replaced by one Play/Pause button under the frame, so nothing covers the video.

## Hooks that must not change

Tests and browser checks rely on these:
- `data-beat`, `data-edge`, `data-rung`, `data-refusal-type`, `data-swap`, `data-rejected-draft`, `aria-label`s;
- the `#locale-select` / `#city-select` ids and option values (now inline in the viewer sentence);
- button names ("End play & view receipt", "Drag up: …", "Ask", "Verify signature", the three suggested questions).

**Text is always a layer:** never bake copy, prices or badges into plates.

## Checking a change

Run from the repo root (`~/.claude/skills/design-taste-frontend` is installed globally on the maintainer's machine):

```bash
node ~/.claude/skills/design-taste-frontend/scripts/lint.mjs frontend/src      # 0 FAIL expected
node ~/.claude/skills/design-taste-frontend/scripts/inspect.mjs "http://localhost:5173/?manifest=m_src_demo_standard&entry_beat=b_offer"
```

The inspector should report 0 FAIL. It warns about font-size count and footage; both are defended, because those sizes are the ad's own copy inside the scaled player, and the hero is the product's moving picture.
