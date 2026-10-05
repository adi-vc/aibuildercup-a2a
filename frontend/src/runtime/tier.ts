/**
 * tier.ts — the degradation ladder (vachan-plan.md §29, §51):
 *   full-res → low-res → still+parallax → still
 *
 * The tier is a network decision. How a given asset renders under a tier
 * also depends on the viewer (reduced motion), the device (WebGL) and the
 * asset (does it have a depth map) — renderPlan() combines them. Both are
 * pure so the ladder is testable without a browser.
 */

export type Tier = 'full' | 'low' | 'still_parallax' | 'still';
export const TIERS: Tier[] = ['full', 'low', 'still_parallax', 'still'];

export interface NetworkEnv {
  saveData?: boolean;
  /** NetworkInformation.effectiveType: 'slow-2g' | '2g' | '3g' | '4g' */
  effectiveType?: string;
  /** `?tier=` — forces a rung, for demos and tests. */
  override?: string | null;
}

export function chooseTier({ saveData, effectiveType, override }: NetworkEnv): Tier {
  if (override && (TIERS as string[]).includes(override)) return override as Tier;
  if (saveData || effectiveType === 'slow-2g') return 'still';
  if (effectiveType === '2g') return 'still_parallax';
  if (effectiveType === '3g') return 'low';
  return 'full';
}

export interface RenderPlan {
  /** Which plate URI to load: the full plate or its (smaller) poster. */
  plate: 'full' | 'poster';
  motion: 'parallax' | 'kenburns' | 'none';
  /** Whether transition clips may play (P6); below `low` edges cut to the still. */
  clips: boolean;
}

export interface ViewerEnv {
  reducedMotion: boolean;
  webgl: boolean;
}

export function renderPlan(tier: Tier, viewer: ViewerEnv, hasDepth: boolean): RenderPlan {
  const motionAllowed = !viewer.reducedMotion && tier !== 'still';
  return {
    plate: tier === 'full' ? 'full' : 'poster',
    motion: !motionAllowed ? 'none' : viewer.webgl && hasDepth ? 'parallax' : 'kenburns',
    // Clips are motion too: reduced motion cuts edges straight to the next still.
    clips: motionAllowed && (tier === 'full' || tier === 'low'),
  };
}

/** Read the live environment once per page. Missing APIs degrade to "full, motion on". */
export function readEnvironment(search: string): { tier: Tier; viewer: ViewerEnv } {
  const nav = navigator as Navigator & { connection?: { saveData?: boolean; effectiveType?: string } };
  const tier = chooseTier({
    saveData: nav.connection?.saveData,
    effectiveType: nav.connection?.effectiveType,
    override: new URLSearchParams(search).get('tier'),
  });
  let webgl: boolean;
  try {
    webgl = !!document.createElement('canvas').getContext('webgl');
  } catch {
    webgl = false;
  }
  const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false;
  return { tier, viewer: { reducedMotion, webgl } };
}
