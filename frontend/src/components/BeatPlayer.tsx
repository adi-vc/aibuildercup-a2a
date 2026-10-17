/**
 * BeatPlayer.tsx — the P5 runtime player.
 *
 * Plays every beat of a manifest through the Remotion composition. Locale and
 * city are profile fields: changing either re-renders the text and binding
 * layers over the same plates, mid-play, with no reload and no generation.
 * The binding readout under the stage shows which §24.2 rung is on screen.
 */

import type React from 'react';
import { useEffect, useState } from 'react';
import { usePlayLog } from '../runtime/usePlayLog';
import type { SignedPlayRecord } from '../runtime/playlog';
import { profileHash } from '../runtime/playlog';
import { Receipt } from './Receipt';
import type { Manifest, ViewerProfile } from '../types/manifest';
import { CITIES } from '../runtime/profile';
import { useBindings } from '../runtime/useBindings';
import type { BindingResolution } from '../runtime/bindings';
import { embedSnippet } from '../runtime/embed';
import { RuntimePlayer } from './RuntimePlayer';
import { QuestionPanel, type AskResponse } from './QuestionPanel';
import styles from './BeatPlayer.module.css';

interface Props {
  manifest: Manifest;
  /** Content version (ETag) of the manifest — the play-log cites it. */
  version: string;
  profile: ViewerProfile;
  onProfileChange?: (p: ViewerProfile) => void;
}

const RUNG_LABEL: Record<BindingResolution['rung'], string> = {
  1: 'Live',
  2: 'Last known',
  3: 'As published',
  4: 'Neutral wording',
};

const LOCALE_NAMES: Record<string, string> = { 'en-IN': 'English', 'hi-IN': 'हिन्दी', 'kn-IN': 'ಕನ್ನಡ' };

const clock = (iso: string) => new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

function describeSource(r: BindingResolution): string {
  switch (r.source.kind) {
    case 'binding': return `${r.source.resolver} · ${clock(r.source.resolved_at)}`;
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
  const [currentProfileHash, setCurrentProfileHash] = useState<string>('');

  // The guard gets the current (coarse, PII-free) profile hash; recompute on a locale/city swap.
  useEffect(() => {
    let cancelled = false;
    profileHash(profile).then((h) => !cancelled && setCurrentProfileHash(h), () => undefined);
    return () => { cancelled = true; };
  }, [profile]);

  const endPlay = async () => {
    setReceiptError(null);
    try {
      setReceipt(await playLog.submit());
    } catch (e) {
      setReceiptError(e instanceof Error ? e.message : String(e));
    }
  };

  const handleQuestionAsked = (question: string, response: AskResponse) => {
    if (response.type === 'answered') {
      playLog.recordQuestion(question, response.answer, response.facts_cited);
    } else {
      playLog.recordRefusal(question, response.refusal_type, response.reason);
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
      <section className={styles.main} aria-label="Player">
        <div className={styles.stage}>
          <RuntimePlayer
            manifest={manifest}
            locale={profile.locale}
            bindings={bindings}
            entryBeat={profile.entry_beat}
            onBeatChange={playLog.onBeatChange}
          />
        </div>
        {receipt && <Receipt record={receipt} manifest={manifest} onClose={() => setReceipt(null)} />}
      </section>

      <aside className={styles.inspector} aria-label="Viewer and provenance">
        <section className={styles.card}>
          <h2 className={styles.cardTitle}>Viewer</h2>
          <div className={styles.controls}>
            <label htmlFor="locale-select" className={styles.field}>
              <span className={styles.controlLabel}>Language</span>
              <select id="locale-select" value={profile.locale} onChange={onLocale} className={styles.select}>
                {manifest.locales.map((l) => <option key={l} value={l}>{LOCALE_NAMES[l] ?? l}</option>)}
              </select>
            </label>
            {manifest.bindings.length > 0 && (
              <label htmlFor="city-select" className={styles.field}>
                <span className={styles.controlLabel}>City</span>
                <select id="city-select" value={profile.city} onChange={onCity} className={styles.select}>
                  {CITIES.map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}
                </select>
              </label>
            )}
          </div>
        </section>

        {Object.values(bindings).length > 0 && (
          <section className={styles.card}>
            <h2 className={styles.cardTitle}>Live values</h2>
            <ul className={styles.bindingReadout} aria-label="Binding resolution">
              {Object.values(bindings).map((r) => (
                <li key={r.key} data-rung={r.rung}>
                  <span className={styles.bindingKey}>{r.key}</span>
                  <span className={styles.bindingRung}>
                    <span className={styles.dot} aria-hidden="true" />
                    {RUNG_LABEL[r.rung]} <span className={styles.rungNo}>· rung {r.rung}</span>
                  </span>
                  <code className={styles.bindingSource}>{describeSource(r)}</code>
                </li>
              ))}
            </ul>
          </section>
        )}

        <section className={styles.card}>
          <button type="button" className={styles.primaryButton} onClick={endPlay}>End play &amp; view receipt</button>
          <p className={styles.hint}>Signs a receipt of exactly what this viewer saw.</p>
          {receiptError && <p className={styles.receiptError} role="alert">{receiptError}</p>}
        </section>

        <section className={styles.card}>
          <dl className={styles.meta}>
            <dt>Manifest</dt>
            <dd><code translate="no">{manifest.manifest_id}</code></dd>
            <dt>Beats</dt>
            <dd>{manifest.beats.length}</dd>
            {version && (
              <>
                <dt>Version</dt>
                <dd><code translate="no">{version.slice(0, 10)}</code></dd>
              </>
            )}
          </dl>
          <EmbedSnippet manifestId={manifest.manifest_id} profile={profile} />
        </section>
      </aside>

      <QuestionPanel
        manifestId={manifest.manifest_id}
        locale={profile.locale}
        city={profile.city}
        profileHash={currentProfileHash}
        apiBaseUrl={import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080'}
        onQuestionAsked={handleQuestionAsked}
      />
    </div>
  );
}
