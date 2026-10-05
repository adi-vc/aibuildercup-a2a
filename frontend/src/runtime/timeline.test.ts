import { describe, expect, it } from 'vitest';
import { beatPosterFrame, HOLD_FRAMES, parallaxOffset, TEXT_SETTLED } from './timeline';
import type { Manifest } from '../types/manifest';

describe('parallaxOffset', () => {
  it('is a pure function of the frame (same frame, same pixels — export matches player)', () => {
    expect(parallaxOffset(37)).toEqual(parallaxOffset(37));
  });

  it('drifts monotonically across the hold and is centred mid-hold', () => {
    const [x0] = parallaxOffset(0);
    const [xm] = parallaxOffset(HOLD_FRAMES / 2);
    const [x1] = parallaxOffset(HOLD_FRAMES);
    expect(x0).toBeLessThan(xm);
    expect(xm).toBeCloseTo(0);
    expect(x1).toBeGreaterThan(xm);
  });

  it('stays inside the 4% overscan so lookups never leave the plate', () => {
    for (const f of [-10, 0, HOLD_FRAMES, HOLD_FRAMES * 3]) {
      const [x, y] = parallaxOffset(f);
      expect(Math.abs(x) * 0.6).toBeLessThan(0.02); // max |depth - 0.4| = 0.6
      expect(Math.abs(y) * 0.6).toBeLessThan(0.02);
    }
  });
});

describe('beatPosterFrame', () => {
  it('lands after the text has settled in the right beat', () => {
    const m = { beats: [{ id: 'a' }, { id: 'b' }] } as unknown as Manifest;
    expect(beatPosterFrame(m, 'b')).toBe(HOLD_FRAMES + TEXT_SETTLED + 2);
  });
});
