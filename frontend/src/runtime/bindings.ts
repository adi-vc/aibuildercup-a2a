/**
 * bindings.ts — play-time binding resolution (vachan-plan.md §24.2, §49 C5).
 *
 * Two halves, deliberately separate:
 *   • decideBinding()  — a PURE function implementing the §24.2 precedence
 *     ladder. Given the cache, the clock and the manifest it returns what to
 *     show and a receipt record. Every rung is either live-and-timestamped or
 *     published-and-cited; there is no rung where the runtime guesses.
 *   • BindingCache     — the C5 cache keyed (resolver, city, sku), filled by
 *     an injected fetcher. A failed fetch writes nothing, so the ladder falls.
 */

import type { Beat, Binding, Manifest } from '../types/manifest';

export type Rung = 1 | 2 | 3 | 4;

export interface LiveValue {
  value: string;
  unit: string;
  resolver: string;
  /** Server timestamp of the resolution — what the receipt records. */
  resolvedAtIso: string;
  /** Client epoch ms when the answer arrived — what TTL ageing uses (immune to clock skew). */
  receivedAt: number;
}

/** What the receipt (P7.5) records for a shown binding — mirrors §24.2's last column. */
export type BindingSource =
  | { kind: 'binding'; resolver: string; resolved_at: string }
  | { kind: 'binding_stale'; resolver: string; age_s: number }
  | { kind: 'fact'; fact_id: string; span_id: string; quote: string }
  | { kind: 'omitted' };

export interface BindingResolution {
  key: string;
  rung: Rung;
  /** Exactly what is rendered on screen. */
  display: string;
  /** Raw value + unit shown (absent for rung 4). */
  value?: string;
  unit?: string;
  source: BindingSource;
}

/** Stale-while-revalidate window past the TTL (§49 C5: 60–300 s). */
export const SWR_WINDOW_S = 300;

const NEUTRAL: Record<string, Record<string, string>> = {
  price: {
    'en-IN': 'On-road price varies by city.',
    'hi-IN': 'ऑन-रोड कीमत शहर के अनुसार अलग होती है।',
  },
};

/** On-screen provenance tags per rung, per locale. */
const TAGS: Record<string, { live: string; lastKnown: (min: number) => string; asPublished: string }> = {
  'en-IN': { live: 'live', lastKnown: (m) => `last known · ${m} min ago`, asPublished: 'as published' },
  'hi-IN': { live: 'लाइव', lastKnown: (m) => `पिछली जानकारी · ${m} मिनट पहले`, asPublished: 'प्रकाशित मूल्य' },
};

export function formatValue(value: string, unit: string | undefined, locale: string): string {
  const n = Number(value);
  if (unit === 'INR' && Number.isFinite(n)) {
    return new Intl.NumberFormat(`${locale}-u-nu-latn`, {
      style: 'currency',
      currency: 'INR',
      maximumFractionDigits: 0,
    }).format(n);
  }
  return unit ? `${value} ${unit}` : value;
}

export function neutralPhrase(key: string, locale: string): string {
  const table = NEUTRAL[key] ?? {};
  return table[locale] ?? table['en-IN'] ?? '';
}

/** The provenance tag shown beside a resolved value: live time, staleness, or "as published". */
export function bindingTag(r: BindingResolution, locale: string): string {
  const t = TAGS[locale] ?? TAGS['en-IN'];
  switch (r.source.kind) {
    case 'binding': {
      const time = new Date(r.source.resolved_at).toLocaleTimeString(locale, { hour: '2-digit', minute: '2-digit' });
      return `${t.live} · ${time}`;
    }
    case 'binding_stale':
      return t.lastKnown(Math.max(1, Math.round(r.source.age_s / 60)));
    case 'fact':
      return t.asPublished;
    case 'omitted':
      return '';
  }
}

/**
 * The rung-3 fallback for a binding: the canon fact the bound beat cites for
 * this city (e.g. `offer_price_bengaluru` for city `bengaluru`), only if the
 * manifest publishes it. Matching is by the `_<city>` suffix the ads adapter
 * uses; a beat citing no such fact has no rung 3.
 */
export function fallbackFactId(manifest: Manifest, key: string, city: string): string | undefined {
  const published = manifest.integrity.facts ?? {};
  const beats: Beat[] = manifest.beats.filter((b) => b.bindings.includes(key));
  for (const beat of beats) {
    const hit = beat.fact_ids.find(
      (fid) => fid.endsWith(`_${city.toLowerCase()}`) && published[fid]?.origin === 'canon',
    );
    if (hit) return hit;
  }
  return undefined;
}

export interface DecideInput {
  binding: Binding;
  manifest: Manifest;
  city: string;
  locale: string;
  /** Last value the resolver returned for (resolver, city), if any. */
  cached: LiveValue | undefined;
  now: number;
}

/** §24.2: live → stale-but-cached → published canon fact → neutral wording. */
export function decideBinding({ binding, manifest, city, locale, cached, now }: DecideInput): BindingResolution {
  const { key } = binding;
  if (cached) {
    const ageS = (now - cached.receivedAt) / 1000;
    if (ageS <= binding.ttl_s) {
      return {
        key, rung: 1, value: cached.value, unit: cached.unit,
        display: formatValue(cached.value, cached.unit, locale),
        source: { kind: 'binding', resolver: cached.resolver, resolved_at: cached.resolvedAtIso },
      };
    }
    if (ageS <= binding.ttl_s + SWR_WINDOW_S) {
      return {
        key, rung: 2, value: cached.value, unit: cached.unit,
        display: formatValue(cached.value, cached.unit, locale),
        source: { kind: 'binding_stale', resolver: cached.resolver, age_s: Math.round(ageS) },
      };
    }
  }
  const factId = fallbackFactId(manifest, key, city);
  const fact = factId ? manifest.integrity.facts?.[factId] : undefined;
  const spanId = factId ? manifest.integrity.fact_index[factId] : undefined;
  if (factId && fact && spanId) {
    return {
      key, rung: 3, value: fact.value, unit: fact.unit,
      display: formatValue(fact.value, fact.unit, locale),
      source: { kind: 'fact', fact_id: factId, span_id: spanId, quote: fact.quote },
    };
  }
  return { key, rung: 4, display: neutralPhrase(key, locale), source: { kind: 'omitted' } };
}

// ── C5 cache ─────────────────────────────────────────────────────────────────

export type BindingFetcher = (
  keys: string[],
  city: string,
) => Promise<{ values: Record<string, { value: string; unit: string; resolver: string }>; resolved_at: string }>;

export class BindingCache {
  private entries = new Map<string, LiveValue>();
  private readonly fetcher: BindingFetcher;
  private readonly sku: string;
  private readonly clock: () => number;

  constructor(fetcher: BindingFetcher, sku = 'vega_v1', clock: () => number = Date.now) {
    this.fetcher = fetcher;
    this.sku = sku;
    this.clock = clock;
  }

  private cacheKey(resolver: string, city: string): string {
    return `${resolver}|${city.toLowerCase()}|${this.sku}`;
  }

  get(binding: Binding, city: string): LiveValue | undefined {
    return this.entries.get(this.cacheKey(binding.resolver, city));
  }

  /** True when every binding has a value inside its TTL — no fetch needed. */
  isFresh(bindings: Binding[], city: string, now: number): boolean {
    return bindings.every((b) => {
      const hit = this.get(b, city);
      return hit !== undefined && (now - hit.receivedAt) / 1000 <= b.ttl_s;
    });
  }

  /**
   * Ask the resolver for these bindings. Success refreshes the cache; any
   * failure (network, 5xx, timeout) is swallowed so callers fall down the
   * ladder. Returns whether the resolver answered.
   */
  async refresh(bindings: Binding[], city: string): Promise<boolean> {
    if (bindings.length === 0) return true;
    try {
      const resp = await this.fetcher(bindings.map((b) => b.key), city);
      const receivedAt = this.clock();
      for (const b of bindings) {
        const v = resp.values[b.key];
        if (v && v.resolver === b.resolver) {
          this.entries.set(this.cacheKey(b.resolver, city), {
            value: v.value, unit: v.unit, resolver: v.resolver, resolvedAtIso: resp.resolved_at, receivedAt,
          });
        }
      }
      return true;
    } catch {
      return false;
    }
  }

  resolveAll(manifest: Manifest, city: string, locale: string, now: number): Record<string, BindingResolution> {
    const out: Record<string, BindingResolution> = {};
    for (const binding of manifest.bindings) {
      out[binding.key] = decideBinding({ binding, manifest, city, locale, cached: this.get(binding, city), now });
    }
    return out;
  }
}
