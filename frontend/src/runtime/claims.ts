/**
 * claims.ts — which facts a beat puts on screen. Shared by the composition
 * (badges) and the play recorder (receipt), so the receipt can only ever list
 * what the viewer could see.
 */

import type { Beat } from '../types/manifest';
import type { BindingResolution } from './bindings';

/** A bound beat cites one fact per city; only the fallback fact actually shown
 *  (rung 3) is a claim on screen. Unbound beats claim every fact they cite. */
export function shownFactIds(beat: Beat, bindings: Record<string, BindingResolution>): string[] {
  if (beat.bindings.length === 0) return beat.fact_ids;
  return beat.bindings
    .map((key) => bindings[key]?.source)
    .flatMap((src) => (src?.kind === 'fact' ? [src.fact_id] : []));
}
