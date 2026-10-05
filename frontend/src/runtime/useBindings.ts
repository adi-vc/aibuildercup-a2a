/**
 * useBindings — React glue for the §24.2 ladder.
 *
 * Renders from the cache immediately (never waits on the network), fetches
 * when the viewer's city has no fresh value, and re-resolves on a timer so a
 * value ages from rung 1 → 2 → 3 on screen exactly as the ladder says.
 */

import { useEffect, useMemo, useState } from 'react';
import { resolveBindings } from '../api/client';
import type { Manifest } from '../types/manifest';
import { BindingCache, type BindingResolution } from './bindings';

const RECHECK_MS = 15_000;

/** One cache per page: city swaps back and forth reuse fresh values (C5). */
const sharedCache = new BindingCache(resolveBindings);

export function useBindings(manifest: Manifest, city: string, locale: string): Record<string, BindingResolution> {
  // The ladder is evaluated against this clock, advanced by each fetch or
  // timer pass, so render stays pure.
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    let cancelled = false;
    const revalidate = async () => {
      if (!sharedCache.isFresh(manifest.bindings, city, Date.now())) {
        await sharedCache.refresh(manifest.bindings, city);
      }
      if (!cancelled) setNow(Date.now());
    };
    void revalidate();
    const id = window.setInterval(revalidate, RECHECK_MS);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [manifest, city]);

  return useMemo(() => sharedCache.resolveAll(manifest, city, locale, now), [manifest, city, locale, now]);
}
