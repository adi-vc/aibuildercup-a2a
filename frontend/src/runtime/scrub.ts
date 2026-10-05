/**
 * scrub.ts — gesture → clip progress (vachan-plan.md §39.6).
 *
 * Drag maps `clamp(dy / threshold, 0, 1)`; past COMMIT_AT on release the clip
 * completes and the branch commits, otherwise it scrubs back. Progress becomes
 * a frame inside the edge segment, and the Player seeks there, so text and
 * badges move with the footage. Hover eases 0→1 over HOVER_MS.
 */

export const COMMIT_AT = 0.8;
export const HOVER_MS = 600;
export const SETTLE_MS = 220;

/** Upward drag distance as a fraction of the threshold (screen y grows downward). */
export function dragProgress(startY: number, y: number, threshold: number): number {
  if (threshold <= 0) return 0;
  return Math.min(1, Math.max(0, (startY - y) / threshold));
}

/** The frame for `progress` within an edge that starts at `edgeStart` and lasts `edgeFrames`. */
export function edgeFrame(edgeStart: number, edgeFrames: number, progress: number): number {
  return edgeStart + Math.round(Math.min(1, Math.max(0, progress)) * (edgeFrames - 1));
}

export function shouldCommit(progress: number): boolean {
  return progress >= COMMIT_AT;
}

/** Move `from` toward `to` at a rate that covers 0→1 in `durationMs`. */
export function stepToward(from: number, to: number, dtMs: number, durationMs: number): number {
  const step = durationMs <= 0 ? 1 : dtMs / durationMs;
  return from < to ? Math.min(to, from + step) : Math.max(to, from - step);
}
