/**
 * useManifest.ts — React hook for loading a Vachan manifest.
 *
 * Returns { manifest, version, loading, error } — version is the server's
 * content ETag, cited by the play-log.
 * Re-fetches whenever manifestId changes; `loading` is derived from whether
 * the settled result belongs to the requested id, so the effect only sets
 * state from the fetch callback.
 */

import { useState, useEffect } from 'react';
import type { Manifest } from '../types/manifest';
import { fetchManifestVersioned } from '../api/client';

interface UseManifestResult {
  manifest: Manifest | null;
  version: string;
  loading: boolean;
  error: string | null;
}

interface Settled {
  id: string;
  manifest: Manifest | null;
  version: string;
  error: string | null;
}

export function useManifest(manifestId: string): UseManifestResult {
  const [settled, setSettled] = useState<Settled | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchManifestVersioned(manifestId)
      .then(({ manifest, version }) => {
        if (!cancelled) setSettled({ id: manifestId, manifest, version, error: null });
      })
      .catch((e: unknown) => {
        if (!cancelled) setSettled({ id: manifestId, manifest: null, version: '', error: e instanceof Error ? e.message : String(e) });
      });
    return () => {
      cancelled = true;
    };
  }, [manifestId]);

  const current = settled?.id === manifestId ? settled : null;
  return {
    manifest: current?.manifest ?? null,
    version: current?.version ?? '',
    loading: current === null,
    error: current?.error ?? null,
  };
}
