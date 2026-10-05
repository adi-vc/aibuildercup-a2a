/**
 * RuntimePlayer.tsx — the Remotion <Player> wired to the runtime: degradation
 * environment, plate prefetch, entry beat, resolved bindings, the viewer's
 * path through the bit graph, and the edge gestures (§39.6). Shared by the
 * full player page and the chromeless embed so both play identically.
 *
 * Gestures. Each outgoing edge of the hold on screen gets an affordance pill
 * (§58). `drag_up`: press the pill and drag up — the edge clip scrubs under
 * the finger, forwards and backwards; release past 0.8 commits the branch,
 * earlier scrubs back to where the viewer was. `click`: hovering previews the
 * clip (eases 0→1 over 600 ms, back on leave); a click commits. Progress is a
 * frame inside the edge segment and the Player seeks there, so the copy and
 * badges move with the footage.
 */

import { Player, type PlayerRef } from '@remotion/player';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { Edge, Manifest } from '../types/manifest';
import type { BindingResolution } from '../runtime/bindings';
import { VachanComposition } from '../runtime/composition';
import {
  branchPath, edgeFrames, posterFrame, segmentIndexAt, spinePath, timeline, totalFrames,
  type Segment,
} from '../runtime/path';
import { prefetchPlates } from '../runtime/prefetch';
import { dragProgress, edgeFrame, HOVER_MS, SETTLE_MS, shouldCommit, stepToward } from '../runtime/scrub';
import { readEnvironment } from '../runtime/tier';
import { FPS, HEIGHT, WIDTH } from '../runtime/timeline';
import styles from './RuntimePlayer.module.css';

interface Props {
  manifest: Manifest;
  locale: string;
  bindings: Record<string, BindingResolution>;
  entryBeat?: string;
  autoPlay?: boolean;
  style?: React.CSSProperties;
  /** Called with the beat on screen whenever it changes (the play-log's clock). */
  onBeatChange?: (beatId: string) => void;
}

interface Gesture {
  edge: Edge;
  mode: 'drag' | 'hover';
  /** Path and frame to restore if the gesture does not commit. */
  basePath: Segment[];
  returnFrame: number;
  wasPlaying: boolean;
  edgeStart: number;
  frames: number;
  progress: number;
  target: number;
  startY: number;
  threshold: number;
  /** Set by a click or a release past 0.8: the outcome is decided and cannot be undone by a hover-leave. */
  committing: boolean;
  /** False until the branched path has rendered; seeking earlier would land in the old timeline. */
  ready: boolean;
}

export function RuntimePlayer({ manifest, locale, bindings, entryBeat, autoPlay = false, style, onBeatChange }: Props) {
  const [env] = useState(() => readEnvironment(window.location.search));
  const entry = entryBeat ?? manifest.beats.find((b) => !b.branch_only)?.id ?? '';
  const playerRef = useRef<PlayerRef>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const [path, setPath] = useState<Segment[]>(() => spinePath(manifest));
  const tl = useMemo(() => timeline(manifest, path), [manifest, path]);
  // Player events can arrive before a re-render; always map frames with the latest timeline.
  const tlRef = useRef(tl);
  useEffect(() => {
    tlRef.current = tl;
  }, [tl]);
  const [initialFrame] = useState(() => posterFrame(timeline(manifest, spinePath(manifest)), entry));
  const [holdIndex, setHoldIndex] = useState(() => segmentIndexAt(tl, initialFrame));
  const gestureRef = useRef<Gesture | null>(null);
  const pendingSeek = useRef<number | null>(null);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    prefetchPlates(manifest, entry, env.tier, env.viewer);
  }, [manifest, entry, env]);

  // A new path changes the Player's duration; seek only once it has rendered.
  useEffect(() => {
    if (pendingSeek.current !== null) {
      playerRef.current?.seekTo(pendingSeek.current);
      pendingSeek.current = null;
    }
    if (gestureRef.current) gestureRef.current.ready = true;
  }, [path]);

  // Which segment is on screen → which hold's pills to show, and the play-log's beat.
  useEffect(() => {
    const player = playerRef.current;
    if (!player) return;
    let current = '';
    const report = (frame: number) => {
      // Mid-gesture the pills stay with the hold the gesture started on.
      if (gestureRef.current) return;
      const latest = tlRef.current;
      const i = segmentIndexAt(latest, frame);
      const seg = latest[i]?.segment;
      if (seg?.kind !== 'hold') return; // an edge in flight is not a new screen
      setHoldIndex(i);
      if (seg.beatId !== current) {
        current = seg.beatId;
        onBeatChange?.(seg.beatId);
      }
    };
    report(player.getCurrentFrame());
    const onFrame = (e: { detail: { frame: number } }) => report(e.detail.frame);
    player.addEventListener('frameupdate', onFrame);
    player.addEventListener('seeked', onFrame);
    return () => {
      player.removeEventListener('frameupdate', onFrame);
      player.removeEventListener('seeked', onFrame);
    };
  }, [onBeatChange]);

  const holdSeg = tl[holdIndex]?.segment;
  const holdBeat = holdSeg?.kind === 'hold' ? manifest.beats.find((b) => b.id === holdSeg.beatId) : undefined;
  const outgoing = (holdBeat?.edges ?? [])
    .map((id) => manifest.edges.find((e) => e.id === id))
    .filter((e): e is Edge => !!e && e.trigger !== 'auto');

  // ── Gesture engine ──────────────────────────────────────────────────────────

  const seekTo = (g: Gesture) => {
    if (g.ready) playerRef.current?.seekTo(edgeFrame(g.edgeStart, g.frames, g.progress));
  };

  const finish = useCallback((g: Gesture) => {
    gestureRef.current = null;
    const player = playerRef.current;
    if (!player) return;
    if (shouldCommit(g.progress)) {
      player.play(); // the clip completes, then the target hold — the branch is taken
    } else {
      pendingSeek.current = g.returnFrame;
      setPath(g.basePath); // not committed: back to exactly where the viewer was
      if (g.wasPlaying) window.setTimeout(() => player.play(), 0);
    }
  }, []);

  /** Ease progress toward the gesture's target, then settle (commit or restore) when released. */
  const animate = useCallback((released: boolean) => {
    if (rafRef.current !== null) cancelAnimationFrame(rafRef.current);
    let last = performance.now();
    const tick = (now: number) => {
      const g = gestureRef.current;
      if (!g) return;
      g.progress = stepToward(g.progress, g.target, now - last, g.mode === 'hover' && !released ? HOVER_MS : SETTLE_MS);
      last = now;
      seekTo(g);
      if (g.progress !== g.target) {
        rafRef.current = requestAnimationFrame(tick);
      } else {
        rafRef.current = null;
        if (released || g.target === 0) finish(g);
      }
    };
    rafRef.current = requestAnimationFrame(tick);
  }, [finish]);

  const begin = (edge: Edge, mode: Gesture['mode'], startY: number): Gesture | null => {
    const player = playerRef.current;
    if (!player || gestureRef.current) return gestureRef.current;
    const wasPlaying = player.isPlaying();
    player.pause();
    const next = branchPath(manifest, path, holdIndex, edge);
    const nextTl = timeline(manifest, next);
    const g: Gesture = {
      edge, mode, basePath: path, returnFrame: player.getCurrentFrame(), wasPlaying,
      edgeStart: nextTl[holdIndex + 1].start, frames: edgeFrames(edge),
      progress: 0, target: 0, startY, committing: false, ready: false,
      threshold: (stageRef.current?.clientHeight ?? 400) * 0.45,
    };
    gestureRef.current = g;
    pendingSeek.current = g.edgeStart;
    setPath(next);
    return g;
  };

  const onDragStart = (edge: Edge) => (e: React.PointerEvent) => {
    e.preventDefault();
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    begin(edge, 'drag', e.clientY);
  };
  const onDragMove = (e: React.PointerEvent) => {
    const g = gestureRef.current;
    if (!g || g.mode !== 'drag') return;
    g.progress = g.target = dragProgress(g.startY, e.clientY, g.threshold);
    if (rafRef.current === null) {
      rafRef.current = requestAnimationFrame(() => {
        rafRef.current = null;
        if (gestureRef.current) seekTo(gestureRef.current);
      });
    }
  };
  const onDragEnd = () => {
    const g = gestureRef.current;
    if (!g || g.mode !== 'drag') return;
    g.committing = shouldCommit(g.progress);
    g.target = g.committing ? 1 : 0;
    animate(true);
  };

  const onHoverStart = (edge: Edge) => () => {
    const g = begin(edge, 'hover', 0);
    if (g && g.mode === 'hover') {
      g.target = 1;
      animate(false);
    }
  };
  const onHoverEnd = () => {
    const g = gestureRef.current;
    if (!g || g.mode !== 'hover' || g.committing) return;
    g.target = 0;
    animate(true);
  };
  const onClickCommit = (edge: Edge) => () => {
    const g = gestureRef.current ?? begin(edge, 'hover', 0);
    if (!g) return;
    g.committing = true; // a click is a decision: never scrub back
    g.target = 1;
    g.progress = Math.max(g.progress, 0.8);
    animate(true);
  };

  return (
    <div ref={stageRef} className={styles.stage}>
      <Player
        // Remount only when the entry beat changes; locale/city swaps keep the playhead.
        key={entry}
        ref={playerRef}
        component={VachanComposition}
        inputProps={{ manifest, locale, bindings, env, path }}
        durationInFrames={totalFrames(tl)}
        // Start on a frame whose text is in, so a paused player is never blank.
        initialFrame={initialFrame}
        fps={FPS}
        compositionWidth={WIDTH}
        compositionHeight={HEIGHT}
        style={{ width: '100%', ...style }}
        controls
        loop
        autoPlay={autoPlay}
        initiallyMuted
        clickToPlay={false}
        acknowledgeRemotionLicense
      />
      {outgoing.length > 0 && (
        <div className={styles.pills}>
          {outgoing.map((edge) =>
            edge.trigger === 'drag_up' ? (
              <button
                key={edge.id}
                type="button"
                className={`${styles.pill} ${styles.drag}`}
                onPointerDown={onDragStart(edge)}
                onPointerMove={onDragMove}
                onPointerUp={onDragEnd}
                onPointerCancel={onDragEnd}
                aria-label={`Drag up: ${edge.label}`}
              >
                ↑ Drag up · {edge.label}
              </button>
            ) : (
              <button
                key={edge.id}
                type="button"
                className={styles.pill}
                onPointerEnter={onHoverStart(edge)}
                onPointerLeave={onHoverEnd}
                onClick={onClickCommit(edge)}
              >
                ▶ {edge.label}
              </button>
            ),
          )}
        </div>
      )}
    </div>
  );
}
