/**
 * BeatPlayer.tsx — the player page, told as five chapters (frontend/DESIGN.md):
 *
 *   Watch    the ad, composed for this viewer; the video sits across the
 *            waterline seam between the monsoon sky and the water
 *   Sources  every figure the ad states, with the span it was verified against
 *   Ask      the claim guard: questions answered from the source, or refused
 *   Receipt  a signed record of exactly what this viewer saw
 *   Embed    one line of HTML for a host page; then the colophon
 *
 * Locale and city are profile fields: changing either re-renders the text and
 * binding layers over the same plates, mid-play, with no reload and no generation.
 */

import type React from 'react';
import { useEffect, useState } from 'react';
import { usePlayLog } from '../runtime/usePlayLog';
import type { SignedPlayRecord } from '../runtime/playlog';
import { profileHash } from '../runtime/playlog';
import { Receipt } from './Receipt';
import { factMark, factsInBeatOrder } from '../runtime/factMark';
import { BANGALORE_STREET, MONSOON_SKYLINE, MUMBAI_TAXIS, WORLD_CREDITS } from '../content/world';
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
      // Clipboard can be blocked (permissions, http); the snippet stays selectable.
    }
  };
  return (
    <div className={styles.embed}>
      <pre className={styles.snippet}><code translate="no">{snippet}</code></pre>
      <button type="button" className={styles.copyButton} onClick={copy} aria-live="polite">
        {copied ? 'Copied to clipboard' : 'Copy embed'}
      </button>
    </div>
  );
}

const reveal = (i: number) => ({ 'data-reveal': '', style: { '--i': i } as React.CSSProperties });

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
    return (
      <section className="chapter" data-field="black">
        <h1 className="headline">This manifest has no beats.</h1>
      </section>
    );
  }

  const set = (patch: Partial<ViewerProfile>) => onProfileChange?.({ ...profile, ...patch });
  const onLocale = (e: React.ChangeEvent<HTMLSelectElement>) => set({ locale: e.target.value });
  const onCity = (e: React.ChangeEvent<HTMLSelectElement>) => set({ city: e.target.value });

  const published = manifest.integrity.facts ?? {};
  const factIds = factsInBeatOrder(manifest.beats, published);

  return (
    <>
      {/* ── Watch: the video across the waterline ─────────────────────────── */}
      <section id="watch" className={`chapter ${styles.hero}`} data-field="blue" aria-labelledby="watch-title">
        <div className={styles.water} aria-hidden="true" />
        <h1 id="watch-title" className={`display ${styles.heroTitle}`} {...reveal(0)}>Every word, kept.</h1>
        <div className={styles.stage} {...reveal(1)}>
          <RuntimePlayer
            manifest={manifest}
            locale={profile.locale}
            bindings={bindings}
            entryBeat={profile.entry_beat}
            onBeatChange={playLog.onBeatChange}
          />
        </div>
        <div className={styles.viewer} {...reveal(2)}>
          <p className={styles.viewerLine}>
            Composed for a viewer
            {manifest.bindings.length > 0 && (
              <>
                {' '}in{' '}
                <label htmlFor="city-select" className="sr-only">City</label>
                <select id="city-select" value={profile.city} onChange={onCity} className={styles.inlineSelect}>
                  {CITIES.map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}
                </select>
              </>
            )}
            {' '}who reads{' '}
            <label htmlFor="locale-select" className="sr-only">Language</label>
            <select id="locale-select" value={profile.locale} onChange={onLocale} className={styles.inlineSelect}>
              {manifest.locales.map((l) => <option key={l} value={l}>{LOCALE_NAMES[l] ?? l}</option>)}
            </select>
            .
          </p>
          {Object.values(bindings).length > 0 && (
            <ul className={styles.bindingReadout} aria-label="Binding resolution">
              {Object.values(bindings).map((r) => (
                <li key={r.key} data-rung={r.rung}>
                  <span className={styles.dot} aria-hidden="true" />
                  The {r.key} on screen is <strong>{RUNG_LABEL[r.rung].toLowerCase()}</strong>
                  <span className={styles.bindingSource}> · {describeSource(r)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      {/* ── Sources: every figure, with the span it was verified against ─── */}
      <section id="sources" className="chapter" data-field="yellow" aria-labelledby="sources-title">
        <div className={styles.board}>
          <div className={styles.boardHead} {...reveal(0)}>
            <h2 id="sources-title" className="headline">Every line is sourced.</h2>
            <p>Each figure appears in the ad only because the spec sheet says it, word for word.</p>
          </div>
          <figure className={styles.boardPhoto} {...reveal(1)}>
            <img src={MUMBAI_TAXIS.src} width={MUMBAI_TAXIS.width} height={MUMBAI_TAXIS.height} alt={MUMBAI_TAXIS.alt} loading="lazy" decoding="async" />
          </figure>
          {factIds.map((fid, i) => {
            const fact = published[fid];
            return (
              <div key={fid} className={styles.tile} {...reveal(i % 4)}>
                <p className={styles.mark}>{factMark(fact)}</p>
                <p className={styles.quote}>“{fact.quote}”</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* ── Ask: the claim guard ──────────────────────────────────────────── */}
      <section id="ask" className={`chapter ${styles.split}`} data-field="blue" aria-labelledby="ask-title">
        <div className={styles.splitText}>
          <h2 id="ask-title" className="display" {...reveal(0)}>Ask it anything.</h2>
          <p className="lead" {...reveal(1)}>
            It answers only from the spec sheet. Ask what the sheet doesn’t say, and it refuses, on screen.
          </p>
          <div {...reveal(2)}>
            <QuestionPanel
              manifestId={manifest.manifest_id}
              locale={profile.locale}
              city={profile.city}
              profileHash={currentProfileHash}
              apiBaseUrl={import.meta.env.VITE_API_BASE_URL || 'http://localhost:8080'}
              onQuestionAsked={handleQuestionAsked}
            />
          </div>
        </div>
        <figure className={styles.splitPhoto} {...reveal(1)}>
          <img src={MONSOON_SKYLINE.src} width={MONSOON_SKYLINE.width} height={MONSOON_SKYLINE.height} alt={MONSOON_SKYLINE.alt} loading="lazy" decoding="async" />
        </figure>
      </section>

      {/* ── Receipt: the first step, already open ─────────────────────────── */}
      <section id="receipt" className={`chapter ${styles.receiptChapter}`} data-field="green" aria-labelledby="receipt-title">
        <div className={styles.receiptText}>
          <h2 id="receipt-title" className="display" {...reveal(0)}>Signed for you.</h2>
          <p {...reveal(1)}>
            End the play and the server signs a record of exactly what this viewer saw: every claim, every price,
            every question, every refusal.
          </p>
        </div>
        <div className={styles.fragment} data-ui {...reveal(1)}>
          {receipt ? (
            <Receipt record={receipt} manifest={manifest} onClose={() => setReceipt(null)} />
          ) : (
            <>
              <p className={styles.fragmentTitle}>This play</p>
              <p className={styles.fragmentBody}>
                Recording every screen shown in <strong>{manifest.manifest_id}</strong>, version{' '}
                <strong>{version ? version.slice(0, 10) : 'unversioned'}</strong>.
              </p>
              <button type="button" className={styles.primaryButton} onClick={endPlay}>End play &amp; view receipt</button>
              {receiptError && <p className={styles.receiptError} role="alert">{receiptError}</p>}
            </>
          )}
        </div>
      </section>

      {/* ── Embed, then the colophon ──────────────────────────────────────── */}
      <section id="embed" className={`chapter ${styles.split} ${styles.closer}`} data-field="black" aria-labelledby="embed-title">
        <div className={styles.splitText}>
          <h2 id="embed-title" className="display" {...reveal(0)}>Put it on your store.</h2>
          <p className="lead" {...reveal(1)}>One line of HTML. The host page runs none of our code.</p>
          <div {...reveal(2)}>
            <EmbedSnippet manifestId={manifest.manifest_id} profile={profile} />
          </div>
        </div>
        <figure className={styles.splitPhoto} {...reveal(1)}>
          <img src={BANGALORE_STREET.src} width={BANGALORE_STREET.width} height={BANGALORE_STREET.height} alt={BANGALORE_STREET.alt} loading="lazy" decoding="async" />
        </figure>
        <footer className={styles.colophon}>
          <p className={styles.bigWordmark} translate="no" aria-hidden="true">Vachan</p>
          <p className={styles.credits}>
            {manifest.beats.length} beats · {manifest.locales.length} languages · coverage {Math.round(manifest.integrity.coverage * 100)}%.
            {' '}Photographs: {WORLD_CREDITS.join('; ')}.
          </p>
        </footer>
      </section>
    </>
  );
}
