/**
 * Receipt.tsx — the one-screen receipt (vachan-plan.md §19 moment 8, slide 12).
 *
 * Top half: what this viewer saw — claims with their quotes, every price with
 * its provenance, locales, refusal count. Bottom half: why to believe it — the
 * server signature, the chain, and a one-click tamper test that edits a copy
 * and shows verification fail.
 */

import { useState } from 'react';
import { fetchChain, verifyPlay, type ChainReport } from '../api/client';
import type { Manifest } from '../types/manifest';
import type { ShownBinding, SignedPlayRecord } from '../runtime/playlog';
import styles from './Receipt.module.css';

function provenance(b: ShownBinding): string {
  switch (b.source.kind) {
    case 'binding': return `live · ${b.source.resolver} @ ${new Date(b.source.resolved_at).toLocaleTimeString()}`;
    case 'binding_stale': return `last known · ${b.source.age_s}s old`;
    case 'fact': return `as published · ${b.source.fact_id} → ${b.source.span_id}`;
    case 'omitted': return 'no value shown (neutral wording)';
  }
}

const short = (s: string) => (s.length > 18 ? `${s.slice(0, 10)}…${s.slice(-6)}` : s);

type Check = 'idle' | 'checking' | 'ok' | 'fail';

export function Receipt({ record, manifest, onClose }: { record: SignedPlayRecord; manifest: Manifest; onClose: () => void }) {
  const [sig, setSig] = useState<Check>('idle');
  const [chain, setChain] = useState<ChainReport | null>(null);
  const [tamper, setTamper] = useState<Check>('idle');

  const claims = new Map<string, string>();
  const prices: { city: string; key: string; binding: ShownBinding }[] = [];
  const seenPrice = new Set<string>();
  for (const seg of record.shown) {
    for (const c of seg.claims) claims.set(c.fact_id, c.span_id);
    for (const [key, b] of Object.entries(seg.bindings)) {
      const id = `${seg.city}|${key}|${b.display}|${b.rung}`;
      if (!seenPrice.has(id)) {
        seenPrice.add(id);
        prices.push({ city: seg.city, key, binding: b });
      }
    }
  }
  const beats = [...new Set(record.shown.map((s) => s.beat_id))];
  // Consecutive distinct values, so a swap reads as "A → B" in viewing order.
  const sequence = (xs: string[]) => xs.filter((x, i) => i === 0 || x !== xs[i - 1]);
  const locales = sequence(record.shown.map((s) => s.locale));
  const cities = sequence(record.shown.map((s) => s.city));
  const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`;

  const verify = async () => {
    setSig('checking');
    setSig((await verifyPlay(record)) ? 'ok' : 'fail');
  };
  const checkChain = async () => setChain(await fetchChain(record.manifest_id));
  const tryTamper = async () => {
    setTamper('checking');
    const forged = structuredClone(record);
    const firstPrice = forged.shown.find((s) => Object.keys(s.bindings).length > 0);
    if (firstPrice) Object.values(firstPrice.bindings)[0].display = '₹99,999';
    else forged.shown[0].locale = forged.shown[0].locale === 'en-IN' ? 'hi-IN' : 'en-IN';
    setTamper((await verifyPlay(forged)) ? 'ok' : 'fail');
  };

  return (
    <section className={styles.receipt} aria-label="Play receipt">
      <header className={styles.head}>
        <h2>Receipt</h2>
        <span>play <code>{record.play_id}</code> · #{record.seq + 1} for <code>{record.manifest_id}</code></span>
        <button type="button" className={styles.close} onClick={onClose} aria-label="Close receipt">Close</button>
      </header>

      <div className={styles.grid}>
        <div>
          <h3>Claims shown ({claims.size})</h3>
          {claims.size === 0 ? <p className={styles.muted}>None. Mood beats only.</p> : (
            <ul>
              {[...claims].map(([fid, span]) => (
                <li key={fid}>
                  “{manifest.integrity.facts?.[fid]?.quote ?? fid}”
                  <small>{fid} → {span}</small>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <h3>Prices shown ({prices.length})</h3>
          {prices.length === 0 ? <p className={styles.muted}>None.</p> : (
            <ul>
              {prices.map(({ city, key, binding }) => (
                <li key={`${city}|${key}|${binding.display}|${binding.rung}`}>
                  <strong>{binding.display}</strong> · {city}
                  <small>rung {binding.rung} · {provenance(binding)}</small>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <h3>Session</h3>
          <ul>
            <li>{plural(beats.length, 'beat')} · {plural(record.shown.length, 'screen')}</li>
            <li>locale: {locales.join(' → ')}</li>
            <li>city: {cities.join(' → ')}</li>
            <li>questions: {record.questions.length} · refusals: {record.refusals.length}</li>
          </ul>
        </div>
      </div>

      <footer className={styles.integrity} aria-live="polite">
        <span>signature <code>{short(record.signature)}</code></span>
        <span>prev <code>{short(record.prev_hash)}</code></span>
        <span>key <code>{record.key_id}</code></span>
        <button type="button" onClick={verify}>Verify signature</button>
        {sig === 'ok' && <b className={styles.ok}>Signature verifies</b>}
        {sig === 'fail' && <b className={styles.bad}>Signature does not verify</b>}
        <button type="button" onClick={checkChain}>Verify chain</button>
        {chain && (chain.ok
          ? <b className={styles.ok}>{chain.count} {chain.count === 1 ? 'play' : 'plays'} chained</b>
          : <b className={styles.bad}>Chain broken at play {(chain.failures[0]?.seq ?? 0) + 1}</b>)}
        <button type="button" onClick={tryTamper}>Try tampering</button>
        {tamper === 'fail' && <b className={styles.ok}>Altered copy rejected</b>}
        {tamper === 'ok' && <b className={styles.bad}>Altered copy verified</b>}
      </footer>
    </section>
  );
}
