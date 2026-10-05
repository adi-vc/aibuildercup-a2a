/**
 * timeline.ts — composition geometry, timing and hold motion, shared by the
 * player, the variant grid and the composition itself. Path-dependent timing
 * (where each segment starts) lives in path.ts.
 */

export const FPS = 30;
export const HOLD_FRAMES = 3 * FPS;
export const WIDTH = 1280;
export const HEIGHT = 720;

/** Text layers fade in over [TEXT_IN_START, TEXT_SETTLED] frames of each hold. */
export const TEXT_IN_START = 6;
export const TEXT_SETTLED = 18;

/**
 * Motion envelope of a hold: 0 on its first and last frame, 1 mid-hold.
 * Every hold therefore begins and ends on its *hinge frame* — the plate with
 * no zoom or drift (§26) — which is the exact first frame of an outgoing edge
 * clip and the exact last frame of an incoming one (§39.3). Pure in the frame.
 */
export function holdMotion(frame: number): number {
  const t = Math.min(1, Math.max(0, frame / (HOLD_FRAMES - 1)));
  return Math.sin(Math.PI * t);
}

/** Ken Burns scale at a frame (fallback motion). */
export function kenBurnsScale(frame: number): number {
  return 1 + 0.06 * holdMotion(frame);
}

/** Parallax camera at a frame: [uv offset x, uv offset y, overscan scale]. The
 *  overscan grows with the drift so displaced lookups stay on the plate, and
 *  returns to 1 (no zoom) at the hinge frames. */
export function parallaxOffset(frame: number): [number, number, number] {
  const s = holdMotion(frame);
  return [0.02 * s, 0.008 * s, 1 - 0.04 * s];
}
