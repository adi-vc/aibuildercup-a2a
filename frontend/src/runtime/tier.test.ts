/** The §29 degradation ladder — network picks the tier, the asset and viewer pick the rendering. */

import { describe, expect, it } from 'vitest';
import { chooseTier, renderPlan } from './tier';

describe('chooseTier', () => {
  it('walks full → low → still+parallax → still as the network worsens', () => {
    expect(chooseTier({ effectiveType: '4g' })).toBe('full');
    expect(chooseTier({ effectiveType: '3g' })).toBe('low');
    expect(chooseTier({ effectiveType: '2g' })).toBe('still_parallax');
    expect(chooseTier({ effectiveType: 'slow-2g' })).toBe('still');
  });

  it('treats Save-Data as the bottom rung, and no NetworkInformation as full', () => {
    expect(chooseTier({ saveData: true, effectiveType: '4g' })).toBe('still');
    expect(chooseTier({})).toBe('full');
  });

  it('honours a valid ?tier= override and ignores junk', () => {
    expect(chooseTier({ effectiveType: '4g', override: 'still' })).toBe('still');
    expect(chooseTier({ effectiveType: '4g', override: 'ultra' })).toBe('full');
  });
});

describe('renderPlan', () => {
  const fast = { reducedMotion: false, webgl: true };

  it('full tier with a depth map: full plate, depth parallax, clips allowed', () => {
    expect(renderPlan('full', fast, true)).toEqual({ plate: 'full', motion: 'parallax', clips: true });
  });

  it('falls back to Ken Burns without a depth map or without WebGL', () => {
    expect(renderPlan('full', fast, false).motion).toBe('kenburns');
    expect(renderPlan('full', { reducedMotion: false, webgl: false }, true).motion).toBe('kenburns');
  });

  it('lower tiers load the poster; still_parallax keeps motion but drops clips', () => {
    expect(renderPlan('low', fast, true)).toEqual({ plate: 'poster', motion: 'parallax', clips: true });
    expect(renderPlan('still_parallax', fast, true)).toEqual({ plate: 'poster', motion: 'parallax', clips: false });
    expect(renderPlan('still', fast, true)).toEqual({ plate: 'poster', motion: 'none', clips: false });
  });

  it('reduced motion stops all motion, clips included, but keeps full resolution on a fast network', () => {
    expect(renderPlan('full', { reducedMotion: true, webgl: true }, true)).toEqual({ plate: 'full', motion: 'none', clips: false });
  });
});
