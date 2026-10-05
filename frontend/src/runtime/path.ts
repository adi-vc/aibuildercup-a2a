/**
 * path.ts — from the bit graph to something a timeline can play (§26).
 *
 * A *path* is the ordered list of segments the viewer will see: holds and the
 * edge clips between them. The default path is the spine — every beat that is
 * not `branch_only`, in manifest order, with a clip wherever an `auto` edge
 * joins two consecutive beats (other joins are cuts, §57). Taking an
 * interactive edge splices `edge → target` into the path after its source
 * hold; playback then rejoins the spine.
 */

import type { Edge, Manifest } from '../types/manifest';
import { FPS, HOLD_FRAMES, TEXT_SETTLED } from './timeline';

export type Segment = { kind: 'hold'; beatId: string } | { kind: 'edge'; edgeId: string };

export interface TimedSegment {
  segment: Segment;
  start: number;
  frames: number;
}

export function edgeFrames(edge: Edge): number {
  return Math.max(1, Math.round(edge.duration_s * FPS));
}

function spineBeats(manifest: Manifest): string[] {
  return manifest.beats.filter((b) => !b.branch_only).map((b) => b.id);
}

function autoEdge(manifest: Manifest, from: string, to: string): Edge | undefined {
  return manifest.edges.find((e) => e.trigger === 'auto' && e.from === from && e.to === to && e.clip);
}

function withAutoEdges(manifest: Manifest, beatIds: string[]): Segment[] {
  const out: Segment[] = [];
  beatIds.forEach((id, i) => {
    out.push({ kind: 'hold', beatId: id });
    const next = beatIds[i + 1];
    const edge = next ? autoEdge(manifest, id, next) : undefined;
    if (edge) out.push({ kind: 'edge', edgeId: edge.id });
  });
  return out;
}

export function spinePath(manifest: Manifest): Segment[] {
  return withAutoEdges(manifest, spineBeats(manifest));
}

/**
 * The path after taking `edge` from the hold at `holdIndex`: everything up to
 * and including that hold, the edge, its target, then the spine continues —
 * after the source beat if the target is a branch, after the target otherwise.
 */
export function branchPath(manifest: Manifest, path: Segment[], holdIndex: number, edge: Edge): Segment[] {
  const head = path.slice(0, holdIndex + 1);
  const target = manifest.beats.find((b) => b.id === edge.to);
  const spine = spineBeats(manifest);
  const resumeAfter = target?.branch_only ? edge.from : edge.to;
  const rest = spine.slice(spine.indexOf(resumeAfter) + 1);
  return [...head, { kind: 'edge', edgeId: edge.id }, { kind: 'hold', beatId: edge.to }, ...withAutoEdges(manifest, rest)];
}

export function timeline(manifest: Manifest, path: Segment[]): TimedSegment[] {
  const edges = new Map(manifest.edges.map((e) => [e.id, e]));
  let start = 0;
  return path.map((segment) => {
    const frames = segment.kind === 'hold' ? HOLD_FRAMES : edgeFrames(edges.get(segment.edgeId)!);
    const timed = { segment, start, frames };
    start += frames;
    return timed;
  });
}

export function totalFrames(tl: TimedSegment[]): number {
  const last = tl[tl.length - 1];
  return Math.max(1, last ? last.start + last.frames : 1);
}

/** The segment index containing `frame` (clamped to the last segment). */
export function segmentIndexAt(tl: TimedSegment[], frame: number): number {
  for (let i = tl.length - 1; i >= 0; i--) if (frame >= tl[i].start) return i;
  return 0;
}

export function firstHoldIndex(tl: TimedSegment[], beatId: string): number {
  return tl.findIndex((t) => t.segment.kind === 'hold' && t.segment.beatId === beatId);
}

/** First frame of a beat's (first) hold with its text fully in — entry points and thumbnails. */
export function posterFrame(tl: TimedSegment[], beatId: string): number {
  const i = firstHoldIndex(tl, beatId);
  return (i < 0 ? 0 : tl[i].start) + TEXT_SETTLED + 2;
}
