/**
 * useManifest.ts — React hook for loading a Vachan manifest.
 *
 * Returns { manifest, loading, error }.
 * Re-fetches whenever manifestId changes.
 */

import { useState, useEffect } from 'react';
import type { Manifest } from '../types/manifest';
import { fetchManifest } from '../api/client';

interface UseManifestResult {
  manifest: Manifest | null;
  loading: boolean;
  error: string | null;
}

export function useManifest(manifestId: string): UseManifestResult {
  const [manifest, setManifest] = useState<Manifest | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetchManifest(manifestId)
      .then((m) => {
        if (!cancelled) {
          setManifest(m);
          setLoading(false);
        }
      })
      .catch((e: unknown) => {
        if (!cancelled) {
          setError(e instanceof Error ? e.message : String(e));
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [manifestId]);

  return { manifest, loading, error };
}
