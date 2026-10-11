/**
 * playlog.ts — what this viewer was shown (vachan-plan.md §31, §64.10).
 *
 * The recorder appends a segment each time the visible screen changes — beat,
 * locale, city, the claims badged on screen, or a binding's displayed value or
 * provenance. The server signs and chains the result (§34: client emits,
 * server attests) after checking every segment against the manifest.
 */

import type { Manifest } from '../types/manifest';
import type { BindingResolution, BindingSource } from './bindings';
import { shownFactIds } from './claims';

export interface ShownBinding {
  display: string;
  rung: 1 | 2 | 3 | 4;
  value?: string;
  unit?: string;
  source: BindingSource;
}

export interface ShownSegment {
  beat_id: string;
  locale: string;
  city: string;
  claims: { fact_id: string; span_id: string }[];
  bindings: Record<string, ShownBinding>;
}

export interface PlayRecord {
  manifest_id: string;
  manifest_version: string;
  profile_hash: string;
  started_at: string;
  ended_at: string;
  shown: ShownSegment[];
  questions: { q: string; a?: string; facts_cited?: string[] }[];
  refusals: { q: string; type: string; reason: string }[];
}

export interface SignedPlayRecord extends PlayRecord {
  play_id: string;
  seq: number;
  prev_hash: string;
  received_at: string;
  key_id: string;
  signature: string;
}

const MAX_SEGMENTS = 500; // server limit

export function segmentFor(
  manifest: Manifest, beatId: string, locale: string, city: string, bindings: Record<string, BindingResolution>,
): ShownSegment | null {
  const beat = manifest.beats.find((b) => b.id === beatId);
  if (!beat) return null;
  const shownBindings: Record<string, ShownBinding> = {};
  for (const key of beat.bindings) {
    const r = bindings[key];
    if (!r) continue;
    shownBindings[key] = {
      display: r.display, rung: r.rung, source: r.source,
      ...(r.value !== undefined && { value: r.value }),
      ...(r.unit !== undefined && { unit: r.unit }),
    };
  }
  return {
    beat_id: beat.id,
    locale,
    city,
    claims: shownFactIds(beat, bindings).map((fid) => ({ fact_id: fid, span_id: manifest.integrity.fact_index[fid] })),
    bindings: shownBindings,
  };
}

export class PlayRecorder {
  private segments: ShownSegment[] = [];
  private questions: { q: string; a?: string; facts_cited?: string[] }[] = [];
  private refusals: { q: string; type: string; reason: string }[] = [];
  private lastKey = '';
  private startedAt: string | null = null;
  private readonly manifest: Manifest;
  private readonly version: string;
  private readonly now: () => string;

  /** One recorder spans the whole play: locale/city swaps are segments, never a new play. */
  constructor(manifest: Manifest, version: string, now: () => string = () => new Date().toISOString()) {
    this.manifest = manifest;
    this.version = version;
    this.now = now;
  }

  /** Record the current screen; a no-op unless something visible changed. Returns true when a play just began. */
  observe(beatId: string, locale: string, city: string, bindings: Record<string, BindingResolution>): boolean {
    const seg = segmentFor(this.manifest, beatId, locale, city, bindings);
    if (!seg) return false;
    const key = JSON.stringify(seg);
    if (key === this.lastKey || this.segments.length >= MAX_SEGMENTS) return false;
    const began = this.startedAt === null;
    this.lastKey = key;
    this.startedAt ??= this.now();
    this.segments.push(seg);
    return began;
  }

  /** Record a question that was answered. */
  recordQuestion(question: string, answer?: string, factsCited?: string[]): void {
    this.questions.push({ q: question, a: answer, facts_cited: factsCited });
  }

  /** Record a refusal. */
  recordRefusal(question: string, type: string, reason: string): void {
    this.refusals.push({ q: question, type, reason });
  }

  get hasContent(): boolean {
    return this.segments.length > 0;
  }

  /** @param profileHash hash of the profile the play *started* with. */
  build(profileHash: string): PlayRecord | null {
    if (!this.startedAt || this.segments.length === 0) return null;
    return {
      manifest_id: this.manifest.manifest_id,
      manifest_version: this.version,
      profile_hash: profileHash,
      started_at: this.startedAt,
      ended_at: this.now(),
      shown: this.segments.map((s) => structuredClone(s)),
      questions: structuredClone(this.questions),
      refusals: structuredClone(this.refusals),
    };
  }

  /** Start a new play. The next observe() opens it with the current screen. */
  reset(): void {
    this.segments = [];
    this.questions = [];
    this.refusals = [];
    this.lastKey = '';
    this.startedAt = null;
  }
}

/** A non-reversible-in-practice tag for the coarse profile — never PII (§43). */
export async function profileHash(profile: { locale: string; city: string; persona?: string; kids_mode: boolean }): Promise<string> {
  const data = new TextEncoder().encode(JSON.stringify([profile.locale, profile.city, profile.persona ?? '', profile.kids_mode]));
  const digest = new Uint8Array(await crypto.subtle.digest('SHA-256', data));
  return 'h_' + Array.from(digest.slice(0, 8), (b) => b.toString(16).padStart(2, '0')).join('');
}
