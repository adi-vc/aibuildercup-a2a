/**
 * RuntimePlayer.tsx — the Remotion <Player> wired to the runtime: degradation
 * environment, plate prefetch, entry beat and resolved bindings. Shared by the
 * full player page and the chromeless embed so both play identically.
 */

import { Player } from '@remotion/player';
import { useEffect, useState } from 'react';
import type { Manifest } from '../types/manifest';
import type { BindingResolution } from '../runtime/bindings';
import { VachanComposition } from '../runtime/composition';
import { prefetchPlates } from '../runtime/prefetch';
import { readEnvironment } from '../runtime/tier';
import { beatPosterFrame, durationFor, FPS, HEIGHT, WIDTH } from '../runtime/timeline';

interface Props {
  manifest: Manifest;
  locale: string;
  bindings: Record<string, BindingResolution>;
  entryBeat?: string;
  autoPlay?: boolean;
  style?: React.CSSProperties;
}

export function RuntimePlayer({ manifest, locale, bindings, entryBeat, autoPlay = false, style }: Props) {
  const [env] = useState(() => readEnvironment(window.location.search));
  const entry = entryBeat ?? manifest.beats[0]?.id ?? '';

  useEffect(() => {
    prefetchPlates(manifest, entry, env.tier, env.viewer);
  }, [manifest, entry, env]);

  return (
    <Player
      // Remount only when the entry beat changes; locale/city swaps keep the playhead.
      key={entry}
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
