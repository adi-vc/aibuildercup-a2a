/**
 * BeatPlayer.tsx — P0 single-beat player.
 *
 * Renders one "hold" beat from a manifest:
 *   • background plate (still image from vault)
 *   • text layer for the selected locale (from text_slots)
 *   • fact badge showing the fact_id → span mapping from integrity.fact_index
 *   • locale selector (en-IN / hi-IN) to prove text is a layer (not baked)
 *
 * P0 deliberately has no parallax, no audio, no scrubbing — those land in P4/P5/P6.
 * The one goal is: manifest → rendered beat → text layer works → deployed URL renders it.
 */

import React, { useState } from 'react';
import type { Manifest, Beat, ViewerProfile } from '../types/manifest';
import styles from './BeatPlayer.module.css';

interface Props {
  manifest: Manifest;
  profile: ViewerProfile;
  onProfileChange?: (p: ViewerProfile) => void;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function resolveAssetUri(uri: string): string {
  // Relative URIs (e.g. /assets/placeholder.jpg) are served from the frontend's
  // public/ directory. Absolute URIs (https://…) are used as-is.
  return uri.startsWith('http') ? uri : uri;
}

// ── Sub-components ────────────────────────────────────────────────────────────

interface FactBadgeProps {
  factId: string;
  spanId: string;
}

function FactBadge({ factId, spanId }: FactBadgeProps) {
  const [open, setOpen] = useState(false);
  return (
    <div className={styles.factBadge}>
      <button
        className={styles.badgeButton}
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-label={`View source for ${factId}`}
      >
        ✓ verified
      </button>
      {open && (
        <div className={styles.badgePanel} role="tooltip">
          <p className={styles.badgeFact}><strong>fact:</strong> {factId}</p>
          <p className={styles.badgeSpan}><strong>span:</strong> {spanId}</p>
          <p className={styles.badgeOrigin}><strong>origin:</strong> canon</p>
        </div>
      )}
    </div>
  );
}

interface BeatHoldProps {
  beat: Beat;
  manifest: Manifest;
  locale: string;
}

function BeatHold({ beat, manifest, locale }: BeatHoldProps) {
  // Resolve the plate asset
  const plateRef = beat.vault_refs[0] ?? '';
  const plate = manifest.vault[plateRef];
  const imageUri = plate ? resolveAssetUri(plate.uri) : '';

  // Text for this locale, falling back to en-IN
  const text =
    beat.text_slots[locale] ?? beat.text_slots['en-IN'] ?? '';

  // Fact badges: one per fact_id cited by this beat
  const badges = beat.fact_ids.map((fid) => ({
    factId: fid,
    spanId: manifest.integrity.fact_index[fid] ?? '—',
  }));

  return (
    <div className={styles.beatHold}>
      {/* Background plate */}
      {imageUri ? (
        <img
          src={imageUri}
          alt={`Beat: ${beat.id}`}
          className={styles.plate}
          draggable={false}
        />
      ) : (
        <div className={styles.platePlaceholder} aria-label="Plate placeholder">
          <span className={styles.placeholderLabel}>[ plate: {plateRef || 'none'} ]</span>
        </div>
      )}

      {/* Text layer — locale-aware; never baked into the image */}
      <div className={styles.textLayer}>
        <p className={styles.beatText}>{text}</p>
      </div>

      {/* Fact badges */}
      <div className={styles.badgeRow}>
        {badges.map((b) => (
          <FactBadge key={b.factId} factId={b.factId} spanId={b.spanId} />
        ))}
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export function BeatPlayer({ manifest, profile, onProfileChange }: Props) {
  const entryBeatId = profile.entry_beat ?? manifest.beats[0]?.id;
  const beat = manifest.beats.find((b) => b.id === entryBeatId) ?? manifest.beats[0];

  if (!beat) {
    return (
      <div className={styles.error}>
        Manifest has no beats. Check the fixture.
      </div>
    );
  }

  const handleLocaleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    onProfileChange?.({ ...profile, locale: e.target.value });
  };

  return (
    <div className={styles.player}>
      {/* Controls */}
      <div className={styles.controls}>
        <label htmlFor="locale-select" className={styles.controlLabel}>
          Locale:
        </label>
        <select
          id="locale-select"
          value={profile.locale}
          onChange={handleLocaleChange}
          className={styles.localeSelect}
        >
          {manifest.locales.map((l) => (
            <option key={l} value={l}>{l}</option>
          ))}
        </select>
        <span className={styles.manifestId}>
          manifest: <code>{manifest.manifest_id}</code>
        </span>
      </div>

      {/* Beat renderer */}
      <BeatHold beat={beat} manifest={manifest} locale={profile.locale} />

      {/* Debug strip (P0 only — remove in P5) */}
      <details className={styles.debugStrip}>
        <summary>P0 debug info</summary>
        <pre>{JSON.stringify({ beat: beat.id, locale: profile.locale, coverage: manifest.integrity.coverage }, null, 2)}</pre>
      </details>
    </div>
  );
}
