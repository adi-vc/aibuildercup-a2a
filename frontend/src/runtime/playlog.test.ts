/** The record must be exactly what was on screen (§64.10 criterion 1). */

import { describe, expect, it } from 'vitest';
import type { Manifest } from '../types/manifest';
import type { BindingResolution } from './bindings';
import { PlayRecorder } from './playlog';

const manifest = {
  manifest_id: 'm', locales: ['en-IN', 'hi-IN'], bindings: [{ key: 'price', resolver: 'offer.by_city', ttl_s: 300 }],
  beats: [
    { id: 'b_hook', fact_ids: [], bindings: [] },
    { id: 'b_flood', fact_ids: ['f_wading_depth'], bindings: [] },
    { id: 'b_offer', fact_ids: ['offer_price_mumbai', 'offer_price_bengaluru'], bindings: ['price'] },
  ],
  integrity: { fact_index: { f_wading_depth: 'sp_1', offer_price_mumbai: 'sp_6', offer_price_bengaluru: 'sp_7' } },
} as unknown as Manifest;

const live: Record<string, BindingResolution> = {
  price: { key: 'price', rung: 1, display: '₹1,29,900', value: '129900', unit: 'INR', source: { kind: 'binding', resolver: 'offer.by_city', resolved_at: 'T' } },
};
const published: Record<string, BindingResolution> = {
  price: { key: 'price', rung: 3, display: '₹1,27,400', value: '127400', unit: 'INR', source: { kind: 'fact', fact_id: 'offer_price_bengaluru', span_id: 'sp_7', quote: 'q' } },
};

describe('PlayRecorder', () => {
  it('records a segment only when the visible screen changes', () => {
    const rec = new PlayRecorder(manifest, 'v1', () => 'now');
    rec.observe('b_hook', 'en-IN', 'mumbai', live);
    rec.observe('b_hook', 'en-IN', 'mumbai', live);      // same screen — no new segment
    rec.observe('b_flood', 'en-IN', 'mumbai', live);
    rec.observe('b_offer', 'en-IN', 'mumbai', live);
    rec.observe('b_offer', 'hi-IN', 'bengaluru', published); // mid-play swap
    const record = rec.build('h')!;
    expect(record.shown.map((s) => [s.beat_id, s.locale, s.city])).toEqual([
      ['b_hook', 'en-IN', 'mumbai'], ['b_flood', 'en-IN', 'mumbai'], ['b_offer', 'en-IN', 'mumbai'], ['b_offer', 'hi-IN', 'bengaluru'],
    ]);
    expect(record.manifest_version).toBe('v1');
    expect(record.profile_hash).toBe('h');
    expect(record.refusals).toEqual([]);
  });

  it('claims are what is badged: all facts on unbound beats, only the cited fallback on bound ones', () => {
    const rec = new PlayRecorder(manifest, 'v1');
    rec.observe('b_flood', 'en-IN', 'mumbai', live);
    rec.observe('b_offer', 'en-IN', 'mumbai', live);
    rec.observe('b_offer', 'en-IN', 'bengaluru', published);
    const [flood, offerLive, offerPublished] = rec.build('h')!.shown;
    expect(flood.claims).toEqual([{ fact_id: 'f_wading_depth', span_id: 'sp_1' }]);
    expect(flood.bindings).toEqual({});                       // a beat without the binding never shows the price
    expect(offerLive.claims).toEqual([]);                      // a live price is not a source claim
    expect(offerLive.bindings.price).toMatchObject({ display: '₹1,29,900', rung: 1 });
    expect(offerPublished.claims).toEqual([{ fact_id: 'offer_price_bengaluru', span_id: 'sp_7' }]);
    expect(offerPublished.bindings.price).toMatchObject({ rung: 3, value: '127400' });
  });

  it('reset starts a fresh play; an empty play builds nothing', () => {
    const rec = new PlayRecorder(manifest, 'v1');
    rec.observe('b_hook', 'en-IN', 'mumbai', live);
    rec.reset();
    expect(rec.build('h')).toBeNull();
    rec.observe('b_hook', 'en-IN', 'mumbai', live);          // same screen as before reset still opens the new play
    expect(rec.build('h')!.shown).toHaveLength(1);
  });

  it('reports when a play begins, so the starting profile can be captured', () => {
    const rec = new PlayRecorder(manifest, 'v1');
    expect(rec.observe('b_hook', 'en-IN', 'mumbai', live)).toBe(true);
    expect(rec.observe('b_flood', 'en-IN', 'mumbai', live)).toBe(false);
  });

  it('ignores beats that are not in the manifest', () => {
    const rec = new PlayRecorder(manifest, 'v1');
    rec.observe('b_ghost', 'en-IN', 'mumbai', live);
    expect(rec.hasContent).toBe(false);
  });
});
