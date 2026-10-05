/**
 * §24.2 ladder — one test per rung, plus the §64.7 criterion-5 kill test:
 * with the resolver down the price is the cited published fact or neutral
 * wording, never an uncited number.
 */

import { describe, expect, it } from 'vitest';
import type { Manifest } from '../types/manifest';
import { BindingCache, bindingTag, decideBinding, SWR_WINDOW_S, type BindingFetcher } from './bindings';

const PRICE = { key: 'price', resolver: 'offer.by_city', ttl_s: 300 };

function manifest(withPublished = true): Manifest {
  return {
    manifest_id: 'm_test', schema_version: '1.0', brain_version: 'br', bitgraph_version: 'bg',
    locales: ['en-IN', 'hi-IN'],
    beats: [{
      id: 'b_offer', kind: 'hold', fact_ids: ['offer_price_mumbai', 'offer_price_bengaluru'],
      vault_refs: ['plate_offer'], text_slots: { 'en-IN': 'Your city price.' }, audio_slots: {},
      bindings: ['price'], hinge: { in: 'wide_neutral', out: 'wide_neutral' }, edges: [],
    }],
    edges: [], slots: [], bindings: [PRICE], vault: {},
    accessibility: { captions: true, audio_description: false },
    policy: { kids_mode: false, competitor_exclusions: [] },
    integrity: {
      fact_index: { offer_price_mumbai: 'sp_6', offer_price_bengaluru: 'sp_7' },
      beat_index: {}, asset_index: {}, coverage: 1, linted_at: '2026-10-06T00:00:00Z',
      ...(withPublished && {
        facts: {
          offer_price_mumbai: { value: '129900', unit: 'INR', text: 'Mumbai', quote: 'Mumbai on-road ₹1,29,900', origin: 'canon' },
          offer_price_bengaluru: { value: '127400', unit: 'INR', text: 'Bengaluru', quote: 'Bengaluru on-road ₹1,27,400', origin: 'canon' },
        },
      }),
    },
  };
}

const T0 = 1_000_000;
const live = (value: string, receivedAt = T0) => ({
  value, unit: 'INR', resolver: 'offer.by_city', resolvedAtIso: '2026-10-06T10:00:00Z', receivedAt,
});
const decide = (cached: ReturnType<typeof live> | undefined, now: number, city = 'mumbai', m = manifest()) =>
  decideBinding({ binding: PRICE, manifest: m, city, locale: 'en-IN', cached, now });

describe('decideBinding — §24.2 ladder', () => {
  it('rung 1: fresh live value within TTL, timestamped', () => {
    const r = decide(live('124900'), T0 + 299_000);
    expect(r.rung).toBe(1);
    expect(r.display).toBe('₹1,24,900');
    expect(r.source).toEqual({ kind: 'binding', resolver: 'offer.by_city', resolved_at: '2026-10-06T10:00:00Z' });
  });

  it('rung 2: past TTL but inside the SWR window, shown with its age', () => {
    const r = decide(live('124900'), T0 + 400_000);
    expect(r.rung).toBe(2);
    expect(r.source).toEqual({ kind: 'binding_stale', resolver: 'offer.by_city', age_s: 400 });
  });

  it('rung 3: beyond SWR the cached value is dropped for the cited published fact', () => {
    const r = decide(live('124900'), T0 + (300 + SWR_WINDOW_S + 1) * 1000);
    expect(r.rung).toBe(3);
    expect(r.value).toBe('129900');
    expect(r.source).toMatchObject({ kind: 'fact', fact_id: 'offer_price_mumbai', span_id: 'sp_6' });
  });

  it('rung 3 picks the fact for the viewer’s city', () => {
    const r = decide(undefined, T0, 'Bengaluru');
    expect(r).toMatchObject({ rung: 3, display: '₹1,27,400', source: { fact_id: 'offer_price_bengaluru' } });
  });

  it('rung 4: no live value and no published fact for this city → neutral wording, no number', () => {
    const r = decide(undefined, T0, 'chennai');
    expect(r.rung).toBe(4);
    expect(r.value).toBeUndefined();
    expect(r.display).not.toMatch(/\d/);
    expect(r.source).toEqual({ kind: 'omitted' });
  });

  it('rung 4 when the manifest publishes no fact values (older manifests)', () => {
    expect(decide(undefined, T0, 'mumbai', manifest(false)).rung).toBe(4);
  });

  it('tags rung 3 "as published" and rung 2 with its age, per locale', () => {
    expect(bindingTag(decide(undefined, T0), 'en-IN')).toBe('as published');
    expect(bindingTag(decide(live('1'), T0 + 400_000), 'en-IN')).toBe('last known · 7 min ago');
    expect(bindingTag(decide(live('1'), T0), 'hi-IN')).toMatch(/^लाइव · /);
  });

  it('localises the neutral phrase', () => {
    const r = decideBinding({ binding: PRICE, manifest: manifest(), city: 'pune', locale: 'hi-IN', cached: undefined, now: T0 });
    expect(r.display).toContain('शहर');
  });
});

describe('BindingCache — resolver killed (§64.7 criterion 5)', () => {
  const ok: BindingFetcher = async (_keys, city) => {
    const values: Awaited<ReturnType<BindingFetcher>>['values'] = {};
    if (city === 'mumbai') values.price = { value: '129900', unit: 'INR', resolver: 'offer.by_city' };
    return { values, resolved_at: '2026-10-06T10:00:00Z' };
  };
  const dead: BindingFetcher = async () => { throw new Error('503'); };

  it('a dead resolver with an empty cache shows the cited fact, never a guessed number', async () => {
    const cache = new BindingCache(dead, 'vega_v1', () => T0);
    expect(await cache.refresh([PRICE], 'bengaluru')).toBe(false);
    const r = cache.resolveAll(manifest(), 'bengaluru', 'en-IN', T0).price;
    expect(r.rung).toBe(3);
    expect(r.source).toMatchObject({ kind: 'fact', fact_id: 'offer_price_bengaluru' });
  });

  it('a dead resolver after a good answer serves last-good inside SWR, then falls to the fact', async () => {
    let fetcher = ok;
    const cache = new BindingCache((k, c) => fetcher(k, c), 'vega_v1', () => T0);
    await cache.refresh([PRICE], 'mumbai');
    fetcher = dead;
    expect(await cache.refresh([PRICE], 'mumbai')).toBe(false);
    expect(cache.resolveAll(manifest(), 'mumbai', 'en-IN', T0 + 310_000).price.rung).toBe(2);
    expect(cache.resolveAll(manifest(), 'mumbai', 'en-IN', T0 + 700_000).price.rung).toBe(3);
  });

  it('every shown number is either live or a cited canon fact', async () => {
    const cache = new BindingCache(dead);
    for (const city of ['mumbai', 'bengaluru', 'delhi', 'chennai']) {
      const r = cache.resolveAll(manifest(), city, 'en-IN', T0).price;
      if (r.value !== undefined) expect(r.source.kind).toMatch(/^(binding|binding_stale|fact)$/);
      else expect(r.rung).toBe(4);
    }
  });

  it('isFresh skips refetch only inside TTL; values are cached per city', async () => {
    const cache = new BindingCache(ok, 'vega_v1', () => T0);
    await cache.refresh([PRICE], 'mumbai');
    expect(cache.isFresh([PRICE], 'mumbai', T0 + 1000)).toBe(true);
    expect(cache.isFresh([PRICE], 'mumbai', T0 + 301_000)).toBe(false);
    expect(cache.isFresh([PRICE], 'bengaluru', T0)).toBe(false);
  });
});
