/**
 * manifest.ts — TypeScript types that mirror the manifest schema (vachan-plan.md §28).
 *
 * Mirrors backend/manifest_schema/manifest.schema.json (frozen at P2, schema 1.0).
 * Builder B owns this file; Builder A's backend emits JSON that must satisfy it.
 */

export type Origin = 'canon' | 'inferred' | 'imagined';
export type Locale = 'en-IN' | 'hi-IN' | 'kn-IN' | string;

// ── Vault asset (plate or clip) ──────────────────────────────────────────────

export interface VaultAsset {
  kind: 'plate' | 'clip' | 'patch' | 'tts';
  uri: string;
  poster_uri?: string;
  depth_uri?: string;
  fact_ids: string[];
  model: string;
  seed: number;
  bible_version: string;
}

// ── Beat ─────────────────────────────────────────────────────────────────────

export interface Hinge {
  in: string;
  out: string;
}

export interface Beat {
  id: string;
  kind: 'hold' | 'transition' | 'ask_overlay';
  /** An atmospheric non-claim beat; it must not cite facts. */
  mood?: boolean;
  fact_ids: string[];
  vault_refs: string[];
  text_slots: Record<Locale, string>;
  audio_slots: Record<Locale, string>;
  bindings: string[];
  hinge: Hinge;
  edges: string[];
}

// ── Edge ─────────────────────────────────────────────────────────────────────

export interface Edge {
  id: string;
  from: string;
  to: string;
  clip: string;
  trigger: 'auto' | 'drag_up' | 'click';
  reversible: boolean;
  duration_s: number;
  label: string;
}

// ── Slot ─────────────────────────────────────────────────────────────────────

export interface SlotPolicy {
  kids_mode: boolean;
  categories_allowed: string[];
  competitor_exclusions: string[];
}

export interface Slot {
  id: string;
  beat_id: string;
  kind: 'shoppable' | 'sponsor_card';
  policy: SlotPolicy;
}

// ── Binding ──────────────────────────────────────────────────────────────────

export interface Binding {
  key: string;
  resolver: string;
  ttl_s: number;
}

// ── Integrity indexes ────────────────────────────────────────────────────────

/** A cited canon fact as published in the manifest (optional, INV-16). */
export interface PublishedFact {
  value: string;
  unit?: string;
  text: string;
  /** Verbatim span text the fact was string-verified against. */
  quote: string;
  origin: Origin;
}

export interface Integrity {
  /** fact_id → span_id (for the badge) */
  fact_index: Record<string, string>;
  /** fact_id → beat_ids (for rebuild) */
  beat_index: Record<string, string[]>;
  /** fact_id → asset_ids (for cache invalidation) */
  asset_index: Record<string, string[]>;
  coverage: number;
  linted_at: string;
  /** fact_id → published value + quote; drives §24.2 rung 3 and the inspector. */
  facts?: Record<string, PublishedFact>;
}

// ── Policy ───────────────────────────────────────────────────────────────────

export interface Policy {
  kids_mode: boolean;
  competitor_exclusions: string[];
}

// ── Accessibility ────────────────────────────────────────────────────────────

export interface Accessibility {
  captions: boolean;
  audio_description: boolean;
}

// ── Manifest (root) ──────────────────────────────────────────────────────────

export interface Manifest {
  manifest_id: string;
  schema_version: string;
  brain_version: string;
  bitgraph_version: string;
  locales: Locale[];
  beats: Beat[];
  edges: Edge[];
  slots: Slot[];
  bindings: Binding[];
  vault: Record<string, VaultAsset>;
  accessibility: Accessibility;
  policy: Policy;
  integrity: Integrity;
  _comment?: string;
}

// ── Profile (viewer) ─────────────────────────────────────────────────────────

export interface ViewerProfile {
  locale: Locale;
  city: string;
  kids_mode: boolean;
  entry_beat?: string;
  persona?: string;
  brand_skin?: string;
}

export const DEFAULT_PROFILE: ViewerProfile = {
  locale: 'en-IN',
  city: 'mumbai',
  kids_mode: false,
};
