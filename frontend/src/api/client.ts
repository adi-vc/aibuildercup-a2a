/**
 * client.ts — thin API client for the Vachan backend.
 *
 * In P0 the player only calls fetchManifest().
 * Later phases add fetchBindings(), askCharacter(), postPlayLog(), etc.
 *
 * The base URL is set from VITE_API_BASE_URL (see .env.example).
 * Falls back to localhost:8080 for local dev so the frontend works without
 * any environment config.
 */

import type { Manifest } from '../types/manifest';

const API_BASE =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8080';

/**
 * Fetch a manifest by id from the backend.
 * In P0 this hits GET /v1/manifest/{id}.
 * In P5+ the player will fetch directly from the CDN URL baked into the embed snippet.
 */
export async function fetchManifest(manifestId: string): Promise<Manifest> {
  const url = `${API_BASE}/v1/manifest/${manifestId}`;
  const resp = await fetch(url);
  if (!resp.ok) {
    const detail = await resp.text().catch(() => resp.statusText);
    throw new Error(`Failed to fetch manifest "${manifestId}": ${resp.status} ${detail}`);
  }
  return resp.json() as Promise<Manifest>;
}

/**
 * POST /v1/sources — ingest a URL and return a source_id + stub facts.
 * Used by the Studio UI (P0 build-time flow), not by the player.
 */
export async function ingestUrl(url: string): Promise<{
  source_id: string;
  gcs_path: string;
  byte_count: number;
  facts_stub: unknown[];
  note: string;
}> {
  const resp = await fetch(`${API_BASE}/v1/sources`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ url }),
  });
  if (!resp.ok) {
    const detail = await resp.text().catch(() => resp.statusText);
    throw new Error(`Ingest failed: ${resp.status} ${detail}`);
  }
  return resp.json();
}
