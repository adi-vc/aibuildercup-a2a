/**
 * embed.ts — the one-line embed (vachan-plan.md §19 moment 9, F26).
 *
 * The snippet is plain HTML: an <iframe> onto our chromeless embed page. The
 * host page runs none of our code and needs no changes beyond the paste; the
 * player inside runs on our origin, so our CORS, Service Worker and cache
 * rules apply unchanged.
 */

import type { ViewerProfile } from '../types/manifest';

export function embedSnippet(origin: string, manifestId: string, profile: Pick<ViewerProfile, 'city' | 'locale'>): string {
  const params = new URLSearchParams({ manifest: manifestId, city: profile.city, locale: profile.locale });
  return `<iframe src="${origin}/embed.html?${params}" title="Interactive video" style="width:100%;aspect-ratio:16/9;border:0" allow="autoplay; fullscreen" loading="lazy"></iframe>`;
}
