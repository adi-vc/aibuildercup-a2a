/**
 * prefetch.ts — warm the plates the viewer will see first (§41 step 2).
 * Requests go through the Service Worker, which keeps them for replays (C4).
 */

import type { Manifest } from '../types/manifest';
import { renderPlan, type Tier, type ViewerEnv } from './tier';

const warmed = new Set<string>();

function warm(uri: string | undefined): void {
  if (!uri || warmed.has(uri)) return;
  warmed.add(uri);
  const img = new Image();
  img.decoding = 'async';
  img.src = uri;
}

/** Prefetch the entry beat and the `ahead` beats after it, per the render plan. */
export function prefetchPlates(manifest: Manifest, entryBeatId: string | undefined, tier: Tier, viewer: ViewerEnv, ahead = 1): void {
  const start = Math.max(0, manifest.beats.findIndex((b) => b.id === entryBeatId));
  for (const beat of manifest.beats.slice(start, start + 1 + ahead)) {
    const asset = manifest.vault[beat.vault_refs[0] ?? ''];
    if (!asset) continue;
    const plan = renderPlan(tier, viewer, !!asset.depth_uri);
    warm(plan.plate === 'poster' ? asset.poster_uri || asset.uri : asset.uri);
    if (plan.motion === 'parallax') warm(asset.depth_uri);
  }
}
