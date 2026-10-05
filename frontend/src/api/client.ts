/**
 * client.ts — thin API client for the Vachan backend.
 *
 * Play-time calls (§35): fetchManifest(), resolveBindings(), submitPlay().
 * P7 adds askCharacter().
 *
 * The base URL is set from VITE_API_BASE_URL (see .env.example).
 * Falls back to localhost:8080 for local dev so the frontend works without
 * any environment config.
 */

import type { Manifest } from '../types/manifest';
import type { BindingFetcher } from '../runtime/bindings';
import type { PlayRecord, SignedPlayRecord } from '../runtime/playlog';

const API_BASE =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8080';

/**
 * Fetch a manifest by id from the backend.
 * In P0 this hits GET /v1/manifest/{id}.
 * In P5+ the player will fetch directly from the CDN URL baked into the embed snippet.
 */
export async function fetchManifest(manifestId: string): Promise<Manifest> {
  return (await fetchManifestVersioned(manifestId)).manifest;
}

/**
 * The manifest plus its version (the server's content ETag). The play-log
 * cites the version so a receipt is bound to the exact manifest played.
 */
export async function fetchManifestVersioned(manifestId: string): Promise<{ manifest: Manifest; version: string }> {
  const url = `${API_BASE}/v1/manifest/${manifestId}`;
  const resp = await fetch(url);
  if (!resp.ok) {
    const detail = await resp.text().catch(() => resp.statusText);
    throw new Error(`Failed to fetch manifest "${manifestId}": ${resp.status} ${detail}`);
  }
  const version = (resp.headers.get('ETag') ?? '').replace(/^W\//, '').replaceAll('"', '');
  return { manifest: (await resp.json()) as Manifest, version };
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

/** A hung resolver must not hold the frame: past this, the §24.2 ladder falls. */
export const BINDINGS_TIMEOUT_MS = 1500;

/**
 * POST /v1/bindings/resolve — play-time values (e.g. price by city).
 * Throws on any failure; BindingCache turns that into a ladder fall.
 */
export const resolveBindings: BindingFetcher = async (keys, city) => {
  const resp = await fetch(`${API_BASE}/v1/bindings/resolve`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ keys, city }),
    signal: AbortSignal.timeout(BINDINGS_TIMEOUT_MS),
  });
  if (!resp.ok) throw new Error(`Binding resolver failed: ${resp.status}`);
  return resp.json();
};

/**
 * POST /v1/playlog — the server validates, signs and chains the record.
 * `keepalive` is for page hide: a text/plain body avoids a CORS preflight the
 * closing page might not survive, and the request outlives the page.
 */
export async function submitPlay(record: PlayRecord, { keepalive = false } = {}): Promise<SignedPlayRecord> {
  const resp = await fetch(`${API_BASE}/v1/playlog`, {
    method: 'POST',
    headers: { 'Content-Type': 'text/plain;charset=UTF-8' },
    body: JSON.stringify(record),
    keepalive,
  });
  if (!resp.ok) {
    const detail = await resp.text().catch(() => resp.statusText);
    throw new Error(`Play record rejected: ${resp.status} ${detail}`);
  }
  return resp.json();
}

/** POST /v1/playlog/verify — recompute the signature over exactly these fields. */
export async function verifyPlay(record: unknown): Promise<boolean> {
  const resp = await fetch(`${API_BASE}/v1/playlog/verify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(record),
  });
  return resp.ok && (await resp.json()).ok === true;
}

export interface ChainReport {
  manifest_id: string;
  ok: boolean;
  count: number;
  failures: { seq: number; play_id: string; reason: string }[];
}

/** GET /v1/playlog/chain/{manifest_id} — every record of the chain, verified. */
export async function fetchChain(manifestId: string): Promise<ChainReport> {
  const resp = await fetch(`${API_BASE}/v1/playlog/chain/${manifestId}`);
  if (!resp.ok) throw new Error(`Chain check failed: ${resp.status}`);
  return resp.json();
}
