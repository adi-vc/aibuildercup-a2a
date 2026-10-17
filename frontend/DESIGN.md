# Vachan design system

How the frontend looks and why. All values live in [`src/styles/tokens.css`](src/styles/tokens.css); change them there, never inline.

## Direction: cinematic automotive

The video is the product, so the interface steps back.

**Principles borrowed from automotive sites** (the Tesla and BMW references in [awesome-design-md](https://github.com/VoltAgent/awesome-design-md)) — not their branding, fonts, colours or marks:
- **Imagery dominates.** The stage gets most of the screen. Chrome is quiet carbon.
- **One message per screen**, one accent. The warm amber `--accent` is reserved for the primary action and the live price. Status colours (`--ok` verified, `--warn` refused) are signals, not decoration.
- **Restraint.**
  - Weights are 400/500 only.
  - Radii are small and concentric (4 / 8 / 14px; the stage tray adds 6px to its inner radius).
  - No decorative shadows or gradients in chrome.
  - The only gradient is the legibility scrim behind on-video copy.
- **One motion curve:** `--ease` (`cubic-bezier(0.32, 0.72, 0, 1)`) at `--dur` (330ms), on `transform`, `opacity` and colours only. `prefers-reduced-motion` turns motion off.

## Tokens

| Group | Tokens |
|---|---|
| Surfaces | `--bg` · `--surface-1/2/3` · `--hairline(-strong)` — dark-first; light parity via `prefers-color-scheme` |
| Text | `--text-1` (primary) · `--text-2` · `--text-3` (labels, meta) |
| Accent and status | `--accent` (+ `-ink`, `-soft`) · `--ok` · `--warn` |
| Type | Geist (`--font-sans`) · Geist Mono (`--font-mono`, IDs and spans) · Noto Sans Devanagari for Hindi, self-hosted via `@fontsource` (no CDN, so the embed's cold start and Service Worker cache stay intact) |
| Scale | `--text-xs … --text-2xl`; tracking `--tracking-tight` for display, `--tracking-label` for small labels |
| Space | 8px grid, `--space-1 … --space-8` |
| Layers | `--z-panel` (ask panel), `--z-grain` (film grain, fixed and non-interactive) |

## Two surfaces, two coordinate systems

1. **Studio chrome** (`App.css`, `components/*.module.css`) is in CSS pixels and follows the theme. The layout is stage + inspector, collapsing to one column under 1060px.
2. **In-video layers** (`runtime/composition.module.css`) are in **composition pixels** (1280×720), scaled by the Remotion Player.
   - They stay dark in both themes, because they sit over imagery.
   - Copy is a left-aligned lower third.
   - Provenance (badges, the spec sheet, the quote panel) is frosted glass.
   - `--controls-clearance` lifts the copy above the player's fixed-size control bar on small screens.

## Rules for new UI

- Use sentence case and plain, specific copy: no exclamation marks, no emoji in UI, no "seamless/elevate" clichés.
- Banned fonts: Inter, Roboto, Arial, Open Sans, Helvetica.
- Numbers that compare or update use `font-variant-numeric: tabular-nums`.
- Every interactive element has hover, `:active` (`scale(0.98)`) and `:focus-visible` (accent outline) states.
- Gestures have a click/keyboard alternative (e.g. Enter on "Drag up" commits the branch).
- **Keep the hooks** tests and browser checks rely on: `data-beat`, `data-edge`, `data-rung`, `data-refusal-type`, `aria-label`s, the `#locale-select` / `#city-select` ids and option values, and button names.
- **Text is always a layer.** Never bake copy, prices or badges into plates.

## Tooling used for the redesign (installed globally on the maintainer's machine, not in the repo)

- **taste-skill** (`npx skills add Leonxlnx/taste-skill -g`): `redesign-existing-projects` drove the audit; `design-taste-frontend` and `high-end-visual-design` set the house style.
- **web-design-guidelines** (`npx skills add vercel-labs/agent-skills -g --skill web-design-guidelines`): the accessibility and interface audit.
- **playwright-cli** (`npm i -g @playwright/cli`): before/after screenshots and regression checks.
