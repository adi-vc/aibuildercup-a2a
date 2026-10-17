/**
 * swapCost.ts — what a viewer-profile swap touched, so the page can show it cost no generation (T12 / F2).
 *
 * The runtime never generates (AGENTS.md §7): a language or city swap re-sets text
 * layers and re-resolves bindings over the same vault pictures. This counts both,
 * from the manifest, so the line on screen is measured rather than asserted.
 */

import type { Manifest, ViewerProfile } from '../types/manifest';

export interface SwapCost {
  language: boolean;
  city: boolean;
  /** Beats whose on-screen copy differs between the two locales. */
  textLayers: number;
  /** Bindings re-resolved for the new city. */
  bindings: number;
  /** Distinct vault pictures (plates and clips) the beats and edges use: all reused. */
  pictures: number;
}

type Shape = Pick<Manifest, 'beats' | 'edges' | 'bindings' | 'vault'>;

export function swapCost(manifest: Shape, prev: ViewerProfile, next: ViewerProfile): SwapCost | null {
  const language = prev.locale !== next.locale;
  const city = prev.city !== next.city;
  if (!language && !city) return null;

  const textLayers = language
    ? manifest.beats.filter((b) => (b.text_slots[prev.locale] ?? '') !== (b.text_slots[next.locale] ?? '')).length
    : 0;
  const refs = new Set([...manifest.beats.flatMap((b) => b.vault_refs), ...manifest.edges.map((e) => e.clip)]);
  const pictures = [...refs].filter((id) => ['plate', 'clip'].includes(manifest.vault[id]?.kind)).length;

  return { language, city, textLayers, bindings: city ? manifest.bindings.length : 0, pictures };
}

/** One sentence for the viewer line, e.g. "That change cost no generation: 9 text layers re-set in Hindi, …". */
export function describeSwap(cost: SwapCost, languageName: string, cityName: string, ms: number | null): string {
  const parts: string[] = [];
  if (cost.language) parts.push(`${cost.textLayers} text ${cost.textLayers === 1 ? 'layer' : 'layers'} re-set in ${languageName}`);
  if (cost.city) parts.push(`the price re-resolved for ${cityName}`);
  parts.push(`the same ${cost.pictures} ${cost.pictures === 1 ? 'picture' : 'pictures'} reused`);
  const timing = ms === null ? '' : `, re-composed in ${Math.max(1, Math.round(ms))} ms`;
  return `That change cost no generation: ${parts.join(', ')}${timing}.`;
}
