/**
 * BeatPlayer.tsx — the P5 runtime player.
 *
 * Plays every beat of a manifest through the Remotion composition. Locale and
 * city are profile fields: changing either re-renders the text and binding
 * layers over the same plates, mid-play, with no reload and no generation.
 * The binding readout under the stage shows which §24.2 rung is on screen.
 */

import type React from 'react';
import { useState } from 'react';
import { usePlayLog } from '../runtime/usePlayLog';
import type { SignedPlayRecord } from '../runtime/playlog';
import { Receipt } from './Receipt';
import type { Manifest, ViewerProfile } from '../types/manifest';
import { CITIES } from '../runtime/profile';
import { useBindings } from '../runtime/useBindings';
import type { BindingResolution } from '../runtime/bindings';
import { embedSnippet } from '../runtime/embed';
import { RuntimePlayer } from './RuntimePlayer';
import styles from './BeatPlayer.module.css';

interface Props {
  manifest: Manifest;
  /** Content version (ETag) of the manifest — the play-log cites it. */
  version: string;
  profile: ViewerProfile;
  onProfileChange?: (p: ViewerProfile) => void;
}

const RUNG_LABEL: Record<BindingResolution['rung'], string> = {
  1: 'live',
  2: 'stale (last known)',
  3: 'published fact',
  4: 'neutral wording',
};

function describeSource(r: BindingResolution): string {
  switch (r.source.kind) {
    case 'binding': return `${r.source.resolver} @ ${r.source.resolved_at}`;
    case 'binding_stale': return `${r.source.resolver}, ${r.source.age_s}s old`;
    case 'fact': return `${r.source.fact_id} → ${r.source.span_id}`;
    case 'omitted': return 'no live value, no published fact for this city';
  }
}

function EmbedSnippet({ manifestId, profile }: { manifestId: string; profile: ViewerProfile }) {
  const [copied, setCopied] = useState(false);
  const snippet = embedSnippet(window.location.origin, manifestId, profile);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(snippet);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard can be blocked (permissions, http); the snippet stays selectable below.
    }
  };
  return (
    <details className={styles.embed}>
      <summary>Embed this video</summary>
      <code className={styles.snippet}>{snippet}</code>
      <button type="button" className={styles.copyButton} onClick={copy}>{copied ? 'Copied ✓' : 'Copy embed'}</button>
    </details>
  );
}

export function BeatPlayer({ manifest, version, profile, onProfileChange }: Props) {
  const bindings = useBindings(manifest, profile.city, profile.locale);
  const playLog = usePlayLog(manifest, version, profile, bindings);
  const [receipt, setReceipt] = useState<SignedPlayRecord | null>(null);
  const [receiptError, setReceiptError] = useState<string | null>(null);

  const endPlay = async () => {
    setReceiptError(null);
    try {
      setReceipt(await playLog.submit());
    } catch (e) {
      setReceiptError(e instanceof Error ? e.message : String(e));
    }
  };

  if (manifest.beats.length === 0) {
    return <div className={styles.error}>Manifest has no beats. Check the fixture.</div>;
  }

  const set = (patch: Partial<ViewerProfile>) => onProfileChange?.({ ...profile, ...patch });
  const onLocale = (e: React.ChangeEvent<HTMLSelectElement>) => set({ locale: e.target.value });
  const onCity = (e: React.ChangeEvent<HTMLSelectElement>) => set({ city: e.target.value });

  return (
    <div className={styles.player}>
      <div className={styles.controls}>
        <label htmlFor="locale-select" className={styles.controlLabel}>Locale</label>
        <select id="locale-select" value={profile.locale} onChange={onLocale} className={styles.select}>
          {manifest.locales.map((l) => <option key={l} value={l}>{l}</option>)}
        </select>
        {manifest.bindings.length > 0 && (
          <>
            <label htmlFor="city-select" className={styles.controlLabel}>City</label>
            <select id="city-select" value={profile.city} onChange={onCity} className={styles.select}>
              {CITIES.map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}
            </select>
          </>
        )}
        <span className={styles.manifestId}>
          manifest: <code>{manifest.manifest_id}</code> · {manifest.beats.length} beats
        </span>
      </div>

      <div className={styles.stage}>
        <RuntimePlayer
          manifest={manifest}
          locale={profile.locale}
          bindings={bindings}
          entryBeat={profile.entry_beat}
          onBeatChange={playLog.onBeatChange}
        />
      </div>

      {Object.values(bindings).length > 0 && (
        <ul className={styles.bindingReadout} aria-label="Binding resolution">
          {Object.values(bindings).map((r) => (
            <li key={r.key} data-rung={r.rung}>
              <code>{r.key}</code> · rung {r.rung} ({RUNG_LABEL[r.rung]}) · <span>{describeSource(r)}</span>
            </li>
          ))}
        </ul>
      )}

      <div className={styles.receiptBar}>
        <button type="button" className={styles.copyButton} onClick={endPlay}>End play &amp; view receipt</button>
        {receiptError && <span className={styles.receiptError}>{receiptError}</span>}
      </div>
      {receipt && <Receipt record={receipt} manifest={manifest} onClose={() => setReceipt(null)} />}

      <EmbedSnippet manifestId={manifest.manifest_id} profile={profile} />
    </div>
  );
}
