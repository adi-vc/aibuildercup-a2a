/**
 * profile.ts — the viewer profile (vachan-plan.md §28). No PII: locale, city,
 * persona and skin only.
 *
 * Sources, later wins: DEFAULT_PROFILE → `?profile=<url to profile.json>` →
 * individual `?locale=` / `?city=` / `?entry_beat=` overrides.
 */

import type { ViewerProfile } from '../types/manifest';
import { DEFAULT_PROFILE } from '../types/manifest';

/** The metric-3 city set (§60: 12 cities × locales). Only cities the source
 *  publishes a price for show a number; the rest fall to neutral wording. */
export const CITIES: { id: string; label: string }[] = [
  { id: 'mumbai', label: 'Mumbai' },
  { id: 'bengaluru', label: 'Bengaluru' },
  { id: 'delhi', label: 'Delhi' },
  { id: 'chennai', label: 'Chennai' },
  { id: 'kolkata', label: 'Kolkata' },
  { id: 'hyderabad', label: 'Hyderabad' },
  { id: 'pune', label: 'Pune' },
  { id: 'ahmedabad', label: 'Ahmedabad' },
  { id: 'jaipur', label: 'Jaipur' },
  { id: 'lucknow', label: 'Lucknow' },
  { id: 'kochi', label: 'Kochi' },
  { id: 'chandigarh', label: 'Chandigarh' },
];

const PROFILE_KEYS: (keyof ViewerProfile)[] = ['locale', 'city', 'kids_mode', 'entry_beat', 'persona', 'brand_skin'];

function pickProfileFields(raw: unknown): Partial<ViewerProfile> {
  if (!raw || typeof raw !== 'object') return {};
  const src = raw as Record<string, unknown>;
  return Object.fromEntries(PROFILE_KEYS.filter((k) => k in src).map((k) => [k, src[k]])) as Partial<ViewerProfile>;
}

export async function loadProfile(search: string): Promise<ViewerProfile> {
  const params = new URLSearchParams(search);
  let profile: ViewerProfile = { ...DEFAULT_PROFILE };
  const profileUrl = params.get('profile');
  if (profileUrl) {
    try {
      const resp = await fetch(profileUrl);
      if (resp.ok) profile = { ...profile, ...pickProfileFields(await resp.json()) };
    } catch {
      // An unreachable profile is not fatal: play with defaults.
    }
  }
  const locale = params.get('locale');
  const city = params.get('city');
  const entryBeat = params.get('entry_beat');
  if (locale) profile.locale = locale;
  if (city) profile.city = city.toLowerCase();
  if (entryBeat) profile.entry_beat = entryBeat;
  return profile;
}
