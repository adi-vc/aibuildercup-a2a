import { describe, expect, it } from 'vitest';
import type { Manifest } from '../types/manifest';
import { branchPath, firstHoldIndex, segmentIndexAt, spinePath, timeline, totalFrames } from './path';
import { dragProgress, edgeFrame, shouldCommit, stepToward } from './scrub';
import { HOLD_FRAMES } from './timeline';

const beat = (id: string, extra = {}) => ({ id, fact_ids: [], bindings: [], edges: [], ...extra });
const manifest = {
  beats: [beat('b_hook'), beat('b_flood'), beat('b_range'), beat('b_charge'), beat('b_offer'), beat('b_spec', { branch_only: true })],
  edges: [
    { id: 'e_auto', from: 'b_hook', to: 'b_flood', clip: 'c0', trigger: 'auto', reversible: false, duration_s: 2, label: '' },
    { id: 'e_spec', from: 'b_flood', to: 'b_spec', clip: 'c1', trigger: 'drag_up', reversible: true, duration_s: 3, label: 'Spec' },
    { id: 'e_offer', from: 'b_range', to: 'b_offer', clip: 'c2', trigger: 'click', reversible: false, duration_s: 2.5, label: 'Price' },
  ],
} as unknown as Manifest;

const ids = (path: ReturnType<typeof spinePath>) => path.map((s) => (s.kind === 'hold' ? s.beatId : `~${s.edgeId}`));

describe('paths', () => {
  it('spine skips branch-only beats and plays auto edges between consecutive beats', () => {
    expect(ids(spinePath(manifest))).toEqual(['b_hook', '~e_auto', 'b_flood', 'b_range', 'b_charge', 'b_offer']);
  });

  it('a branch edge splices edge → target after its source, then rejoins the spine after the source', () => {
    const spine = spinePath(manifest);
    const at = spine.findIndex((s) => s.kind === 'hold' && s.beatId === 'b_flood');
    expect(ids(branchPath(manifest, spine, at, manifest.edges[1]))).toEqual(
      ['b_hook', '~e_auto', 'b_flood', '~e_spec', 'b_spec', 'b_range', 'b_charge', 'b_offer']);
  });

  it('an edge to a spine beat jumps ahead and continues after the target', () => {
    const spine = spinePath(manifest);
    const at = spine.findIndex((s) => s.kind === 'hold' && s.beatId === 'b_range');
    expect(ids(branchPath(manifest, spine, at, manifest.edges[2]))).toEqual(
      ['b_hook', '~e_auto', 'b_flood', 'b_range', '~e_offer', 'b_offer']);
  });

  it('the prefix before a branch keeps its frames, so taking an edge never moves the playhead', () => {
    const spine = timeline(manifest, spinePath(manifest));
    const at = firstHoldIndex(spine, 'b_flood');
    const branched = timeline(manifest, branchPath(manifest, spinePath(manifest), at, manifest.edges[1]));
    expect(branched.slice(0, at + 1)).toEqual(spine.slice(0, at + 1));
    expect(branched[at + 1]).toMatchObject({ start: spine[at].start + HOLD_FRAMES, frames: 90 });
  });

  it('maps frames to segments and sums durations', () => {
    const tl = timeline(manifest, spinePath(manifest));
    expect(totalFrames(tl)).toBe(5 * HOLD_FRAMES + 60);
    expect(segmentIndexAt(tl, 0)).toBe(0);
    expect(segmentIndexAt(tl, HOLD_FRAMES + 59)).toBe(1);
    expect(segmentIndexAt(tl, HOLD_FRAMES + 60)).toBe(2);
  });
});

describe('scrub math (§39.6)', () => {
  it('maps an upward drag to 0..1 and clamps both ways', () => {
    expect(dragProgress(500, 500, 200)).toBe(0);
    expect(dragProgress(500, 400, 200)).toBe(0.5);
    expect(dragProgress(500, 100, 200)).toBe(1);
    expect(dragProgress(500, 650, 200)).toBe(0);
  });

  it('is reversible: moving the finger back reduces the frame', () => {
    const up = edgeFrame(1000, 90, dragProgress(500, 380, 200));
    const back = edgeFrame(1000, 90, dragProgress(500, 450, 200));
    expect(back).toBeLessThan(up);
    expect(edgeFrame(1000, 90, 0)).toBe(1000);
    expect(edgeFrame(1000, 90, 1)).toBe(1089);
  });

  it('commits at 0.8 and not before', () => {
    expect(shouldCommit(0.79)).toBe(false);
    expect(shouldCommit(0.8)).toBe(true);
  });

  it('eases toward a target at a fixed rate without overshoot', () => {
    expect(stepToward(0, 1, 300, 600)).toBe(0.5);
    expect(stepToward(0.9, 1, 300, 600)).toBe(1);
    expect(stepToward(0.2, 0, 300, 600)).toBe(0);
  });
});
