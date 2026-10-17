/**
 * factMark.ts — the large figure a published fact shows on its tile
 * (the "Sources" chapter): its own value and unit, formatted for reading.
 * Only the fact's verified value is used; nothing is rounded or restated.
 */

import type { PublishedFact } from '../types/manifest';

export function factMark(fact: Pick<PublishedFact, 'value' | 'unit'>): string {
  const value = fact.value.trim();
  const unit = (fact.unit ?? '').trim();
  if (unit === 'INR' && /^\d+$/.test(value)) {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(Number(value));
  }
  const hm = value.match(/^(\d+)h(\d+)m$/i);
  if (hm) return `${hm[1]} h ${hm[2]} m`;
  const yr = value.match(/^(\d+)\s*yr\b/i);
  if (yr) return `${yr[1]} years`;
  return unit ? `${value} ${unit}` : value;
}

/** Cited fact ids in the order the ad shows them (beat order), each once. */
export function factsInBeatOrder(beats: { fact_ids: string[] }[], published: Record<string, unknown>): string[] {
  const seen = new Set<string>();
  for (const b of beats) for (const f of b.fact_ids) if (f in published) seen.add(f);
  for (const f of Object.keys(published)) seen.add(f);
  return [...seen];
}
