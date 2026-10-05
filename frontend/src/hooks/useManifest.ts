/**
 * useManifest.ts — React hook for loading a Vachan manifest.
 *
 * Returns { manifest, loading, error }.
 * Re-fetches whenever manifestId changes; `loading` is derived from whether
 * the settled result belongs to the requested id, so the effect only sets
 * state from the fetch callback.
 */

import { useState, useEffect } from 'react';
import type { Manifest } from '../types/manifest';
import { fetchManifest } from '../api/client';

interface UseManifestResult {
  manifest: Manifest | null;
  loading: boolean;
  error: string | null;
}

interface Settled {
  id: string;
  manifest: Manifest | null;
  error: string | null;
}

export function useManifest(manifestId: string): UseManifestResult {
  const [settled, setSettled] = useState<Settled | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchManifest(manifestId)
      .then((m) => {
        if (!cancelled) setSettled({ id: manifestId, manifest: m, error: null });
      })
      .catch((e: unknown) => {
        if (!cancelled) setSettled({ id: manifestId, manifest: null, error: e instanceof Error ? e.message : String(e) });
      });
    return () => {
      cancelled = true;
    };
  }, [manifestId]);

  const current = settled?.id === manifestId ? settled : null;
  return { manifest: current?.manifest ?? null, loading: current === null, error: current?.error ?? null };
}
