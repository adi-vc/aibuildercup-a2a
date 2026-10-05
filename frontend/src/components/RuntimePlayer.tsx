/**
 * RuntimePlayer.tsx — the Remotion <Player> wired to the runtime: degradation
 * environment, plate prefetch, entry beat and resolved bindings. Shared by the
 * full player page and the chromeless embed so both play identically.
 */

import { Player, type PlayerRef } from '@remotion/player';
import { useEffect, useRef, useState } from 'react';
import type { Manifest } from '../types/manifest';
import type { BindingResolution } from '../runtime/bindings';
import { VachanComposition } from '../runtime/composition';
import { prefetchPlates } from '../runtime/prefetch';
import { readEnvironment } from '../runtime/tier';
import { beatPosterFrame, durationFor, FPS, HEIGHT, HOLD_FRAMES, WIDTH } from '../runtime/timeline';

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

export function RuntimePlayer({ manifest, locale, bindings, entryBeat, autoPlay = false, style, onBeatChange }: Props) {
  const [env] = useState(() => readEnvironment(window.location.search));
  const entry = entryBeat ?? manifest.beats[0]?.id ?? '';
  const playerRef = useRef<PlayerRef>(null);

  useEffect(() => {
    const player = playerRef.current;
    if (!player || !onBeatChange) return;
    let current = '';
    const report = (frame: number) => {
      const beat = manifest.beats[Math.min(manifest.beats.length - 1, Math.floor(frame / HOLD_FRAMES))];
      if (beat && beat.id !== current) {
        current = beat.id;
        onBeatChange(beat.id);
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
  }, [manifest, entry, onBeatChange]);

  useEffect(() => {
    prefetchPlates(manifest, entry, env.tier, env.viewer);
  }, [manifest, entry, env]);

  return (
    <Player
      // Remount only when the entry beat changes; locale/city swaps keep the playhead.
      key={entry}
      ref={playerRef}
      component={VachanComposition}
      inputProps={{ manifest, locale, bindings, env }}
      durationInFrames={durationFor(manifest)}
      // Start on a frame whose text is in, so a paused player is never blank.
      initialFrame={beatPosterFrame(manifest, entry)}
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
  );
}
