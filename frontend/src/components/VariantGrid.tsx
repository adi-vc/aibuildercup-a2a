/**
 * VariantGrid.tsx — metric 3 / §64.7 criteria 1–2: many viewers, one manifest.
 *
 * Renders every locale × city (× the kids manifest, when one exists) as a
 * Remotion <Thumbnail> of the bound beat, then lists every network request
 * the page made. The proof is the ledger: manifests, plates and binding
 * lookups only — zero generation calls.
 */

import { Thumbnail } from '@remotion/player';
import { useEffect, useState } from 'react';
import { fetchManifest, resolveBindings } from '../api/client';
import type { Manifest } from '../types/manifest';
import { BindingCache } from '../runtime/bindings';
import { VachanComposition } from '../runtime/composition';
import { posterFrame, spinePath, timeline, totalFrames } from '../runtime/path';
import { FPS, HEIGHT, WIDTH } from '../runtime/timeline';
import { CITIES } from '../runtime/profile';
import { readEnvironment } from '../runtime/tier';
import styles from './VariantGrid.module.css';

/** Any request matching this would be a play-time generation call (§22). */
const GENERATION_PATTERN = /generate|vault\/build|veo|imagen|gemini|aiplatform|texttospeech|lyria/i;

interface LedgerRow { path: string; count: number; generation: boolean }

function readLedger(): LedgerRow[] {
  const rows = new Map<string, LedgerRow>();
  for (const e of performance.getEntriesByType('resource')) {
    const url = new URL(e.name);
    if (url.pathname.startsWith('/@') || url.pathname.startsWith('/node_modules') || url.pathname.startsWith('/src')) continue; // Vite dev modules
    const path = `${url.host}${url.pathname}`;
    const row = rows.get(path) ?? { path, count: 0, generation: GENERATION_PATTERN.test(e.name) };
    row.count += 1;
    rows.set(path, row);
  }
  return [...rows.values()].sort((a, b) => a.path.localeCompare(b.path));
}

async function loadSiblings(manifest: Manifest): Promise<Manifest[]> {
  if (!manifest.manifest_id.endsWith('_standard')) return [manifest];
  try {
    return [manifest, await fetchManifest(manifest.manifest_id.replace(/_standard$/, '_kids'))];
  } catch {
    return [manifest];
  }
}

export function VariantGrid({ manifest }: { manifest: Manifest }) {
  const [manifests, setManifests] = useState<Manifest[]>([manifest]);
  const [cache] = useState(() => new BindingCache(resolveBindings));
  const [resolvedAt, setResolvedAt] = useState<number | null>(null);
  const [ledger, setLedger] = useState<LedgerRow[]>([]);
  // Thumbnails are stills: render them on the `still` rung (no WebGL context
  // per cell — browsers cap live contexts at ~16).
  const [env] = useState(() => ({ ...readEnvironment(window.location.search), tier: 'still' as const }));

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const all = await loadSiblings(manifest);
      await Promise.all(CITIES.map((c) => cache.refresh(manifest.bindings, c.id)));
      if (cancelled) return;
      setManifests(all);
      setResolvedAt(Date.now());
      // Give thumbnails a moment to request their plates before reading the ledger.
      window.setTimeout(() => !cancelled && setLedger(readLedger()), 1500);
    })();
    return () => { cancelled = true; };
  }, [manifest, cache]);

  if (resolvedAt === null) return <div className={styles.note}>Resolving bindings for {CITIES.length} cities…</div>;

  const variants = manifests.flatMap((m) =>
    m.locales.flatMap((locale) => CITIES.map((city) => ({ m, locale, city }))),
  );
  const generationCalls = ledger.filter((r) => r.generation).reduce((n, r) => n + r.count, 0);

  return (
    <div className={styles.wrap}>
      <p className={styles.summary}>
        <strong>{variants.length} variants</strong> from {manifests.length} manifest{manifests.length > 1 ? 's' : ''}
        {' '}({manifests.map((m) => m.manifest_id).join(', ')}) ·{' '}
        <strong data-testid="generation-calls">{generationCalls} generation calls</strong>
      </p>

      <div className={styles.grid}>
        {variants.map(({ m, locale, city }) => {
          const bound = m.beats.find((b) => b.bindings.length > 0) ?? m.beats[0];
          const bindings = cache.resolveAll(m, city.id, locale, resolvedAt);
          const path = spinePath(m);
          const tl = timeline(m, path);
          return (
            <figure key={`${m.manifest_id}|${locale}|${city.id}`} className={styles.cell}>
              <Thumbnail
                component={VachanComposition}
                inputProps={{ manifest: m, locale, bindings, env, path }}
                compositionWidth={WIDTH}
                compositionHeight={HEIGHT}
                durationInFrames={totalFrames(tl)}
                fps={FPS}
                frameToDisplay={posterFrame(tl, bound.id)}
                style={{ width: '100%' }}
              />
              <figcaption>
                {city.label} · {locale}{m.policy.kids_mode ? ' · kids' : ''} · rung {bindings.price?.rung ?? '–'}
              </figcaption>
            </figure>
          );
        })}
      </div>

      <section className={styles.ledger} aria-label="Network ledger">
        <h2>Network ledger</h2>
        {ledger.length === 0 ? <p className={styles.note}>Collecting…</p> : (
          <table>
            <thead><tr><th>request</th><th>count</th><th>generation?</th></tr></thead>
            <tbody>
              {ledger.map((r) => (
                <tr key={r.path} className={r.generation ? styles.bad : undefined}>
                  <td><code>{r.path}</code></td><td>{r.count}</td><td>{r.generation ? 'YES' : 'no'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
