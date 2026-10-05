import { describe, expect, it } from 'vitest';
import { HOLD_FRAMES, holdMotion, kenBurnsScale, parallaxOffset, TEXT_SETTLED } from './timeline';
import { posterFrame, spinePath, timeline } from './path';
import type { Manifest } from '../types/manifest';

describe('hold motion', () => {
  it('starts and ends every hold on the hinge frame (no zoom, no drift, no overscan)', () => {
    for (const f of [0, HOLD_FRAMES - 1]) {
      expect(holdMotion(f)).toBeCloseTo(0, 12);
      expect(kenBurnsScale(f)).toBeCloseTo(1, 12);
      const [x, y, s] = parallaxOffset(f);
      expect([x, y, s].map((v) => +v.toFixed(12))).toEqual([0, 0, 1]);
    }
  });

  it('is a pure function of the frame (same frame, same pixels — export matches player)', () => {
    expect(parallaxOffset(37)).toEqual(parallaxOffset(37));
  });

  it('keeps displaced lookups inside the overscan at peak motion', () => {
    const [x, y, s] = parallaxOffset((HOLD_FRAMES - 1) / 2);
    const margin = (1 - s) / 2;              // uv margin freed by the overscan on each side
    expect(Math.abs(x) * 0.6).toBeLessThanOrEqual(margin);   // max |depth - 0.4| = 0.6
    expect(Math.abs(y) * 0.6).toBeLessThanOrEqual(margin);
  });
});

describe('posterFrame', () => {
  it('lands after the text has settled in the right hold of the path', () => {
    const m = { beats: [{ id: 'a' }, { id: 'b' }], edges: [] } as unknown as Manifest;
    const tl = timeline(m, spinePath(m));
    expect(posterFrame(tl, 'b')).toBe(HOLD_FRAMES + TEXT_SETTLED + 2);
  });
});
