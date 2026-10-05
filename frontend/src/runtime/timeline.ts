/**
 * timeline.ts — composition geometry and timing, shared by the player, the
 * variant grid and the composition itself.
 */

import type { Manifest } from '../types/manifest';

export const FPS = 30;
export const HOLD_FRAMES = 3 * FPS;
export const WIDTH = 1280;
export const HEIGHT = 720;

/** Text layers fade in over [TEXT_IN_START, TEXT_SETTLED] frames of each hold. */
export const TEXT_IN_START = 6;
export const TEXT_SETTLED = 18;

export function durationFor(manifest: Manifest): number {
  return Math.max(1, manifest.beats.length) * HOLD_FRAMES;
}

/** The frame a given beat starts on — used by the variant grid's thumbnails. */
export function beatStartFrame(manifest: Manifest, beatId: string): number {
  return Math.max(0, manifest.beats.findIndex((b) => b.id === beatId)) * HOLD_FRAMES;
}

/** First frame of a beat with its text fully in — for entry points and thumbnails. */
export function beatPosterFrame(manifest: Manifest, beatId: string): number {
  return beatStartFrame(manifest, beatId) + TEXT_SETTLED + 2;
}
