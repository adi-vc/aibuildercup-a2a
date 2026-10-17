import { describe, expect, it } from 'vitest';
import { describeSwap, swapCost } from './swapCost';
import type { Manifest, ViewerProfile } from '../types/manifest';

const asset = (kind: 'plate' | 'clip' | 'tts') => ({ kind, uri: '', fact_ids: [], model: '', seed: 0, bible_version: '' });

const manifest = {
  beats: [
    { vault_refs: ['p1'], text_slots: { 'en-IN': 'Rain.', 'hi-IN': 'बारिश।' } },
    { vault_refs: ['p1', 'p2', 'a1'], text_slots: { 'en-IN': '₹1,29,900', 'hi-IN': '₹1,29,900' } },
    { vault_refs: ['p3'], text_slots: { 'en-IN': '30 cm' } },
  ],
  edges: [{ clip: 'c1' }, { clip: 'p2' }],
  bindings: [{ key: 'price', resolver: 'r', ttl_s: 60 }],
  vault: { p1: asset('plate'), p2: asset('plate'), p3: asset('plate'), c1: asset('clip'), a1: asset('tts') },
} as unknown as Manifest;

const en: ViewerProfile = { locale: 'en-IN', city: 'mumbai', kids_mode: false };

describe('swapCost', () => {
  it('is null when nothing changed', () => {
    expect(swapCost(manifest, en, { ...en })).toBeNull();
  });

  it('counts changed text layers and reuses every picture on a language swap', () => {
    // beat 2 has identical copy; beat 3 has no Hindi slot, so it changes ('30 cm' → '')
    expect(swapCost(manifest, en, { ...en, locale: 'hi-IN' })).toEqual(
      { language: true, city: false, textLayers: 2, bindings: 0, pictures: 4 });
  });

  it('re-resolves the bindings on a city swap', () => {
    expect(swapCost(manifest, en, { ...en, city: 'bengaluru' })).toMatchObject({ city: true, textLayers: 0, bindings: 1 });
  });
});

describe('describeSwap', () => {
  it('reads as one sentence', () => {
    const cost = { language: true, city: false, textLayers: 9, bindings: 0, pictures: 7 };
    expect(describeSwap(cost, 'Hindi', 'Mumbai', 12.4)).toBe(
      'That change cost no generation: 9 text layers re-set in Hindi, the same 7 pictures reused, re-composed in 12 ms.');
    expect(describeSwap({ ...cost, language: false, city: true, pictures: 1 }, 'Hindi', 'Bengaluru', null)).toBe(
      'That change cost no generation: the price re-resolved for Bengaluru, the same 1 picture reused.');
  });
});
