/**
 * App.tsx — P5 root.
 *
 *   ?manifest=<id>   which manifest to play (default: the P2 golden fixture)
 *   ?locale= ?city=  profile overrides; ?profile=<url> loads a profile.json
 *   ?variants=1      the metric-3 variant grid + network ledger
 */

import { useEffect, useRef, useState } from 'react';
import { useManifest } from './hooks/useManifest';
import { BeatPlayer } from './components/BeatPlayer';
import { VariantGrid } from './components/VariantGrid';
import type { ViewerProfile } from './types/manifest';
import { DEFAULT_PROFILE } from './types/manifest';
import { loadProfile } from './runtime/profile';
import { useChapters } from './runtime/useChapters';
import './App.css';

const urlParams = new URLSearchParams(window.location.search);
const MANIFEST_ID = urlParams.get('manifest') ?? 'p0_single_beat';
const SHOW_VARIANTS = urlParams.get('variants') === '1';

export default function App() {
  const { manifest, version, loading, error } = useManifest(MANIFEST_ID);
  const [profile, setProfile] = useState<ViewerProfile>(DEFAULT_PROFILE);

  useEffect(() => {
    loadProfile(window.location.search).then(setProfile);
  }, []);

  const header = useRef<HTMLElement>(null);
  useChapters(header, [manifest, SHOW_VARIANTS]);

  const params = new URLSearchParams(window.location.search);
  params.delete('variants');
  const playerHref = `?${params}`;
  params.set('variants', '1');
  const variantsHref = `?${params}`;
  const chapter = (id: string) => (SHOW_VARIANTS ? `${playerHref}#${id}` : `#${id}`);

  return (
    <div className="app">
      <a className="skip-link" href="#main">Skip to player</a>
      <header className="site-header" ref={header} data-field="blue">
        <a className="wordmark" href={playerHref} translate="no" aria-label="Vachan, player">Vachan</a>
        <nav className="site-nav" aria-label="Chapters">
          <a href={chapter('watch')}>Watch</a>
          <a href={chapter('sources')}>Sources</a>
          <a href={chapter('ask')}>Ask</a>
          <a href={chapter('receipt')}>Receipt</a>
          <a href={variantsHref} aria-current={SHOW_VARIANTS ? 'page' : undefined}>Variants</a>
        </nav>
        <a className="header-action" href={chapter('embed')}>Get the embed</a>
      </header>

      <main id="main" tabIndex={-1}>
        {loading && (
          <section className="chapter loading" data-field="blue" aria-busy="true" aria-label={`Loading manifest ${MANIFEST_ID}…`}>
            <p className="lead">Loading the ad…</p>
          </section>
        )}

        {error && (
          <section className="chapter" data-field="black" role="alert">
            <h1 className="headline">The ad didn’t load.</h1>
            <p className="lead error-detail">{error}</p>
            <p>Check the API is running: <code>uvicorn app.main:app --port 8080</code>.</p>
          </section>
        )}

        {manifest && (SHOW_VARIANTS ? (
          <VariantGrid manifest={manifest} />
        ) : (
          <BeatPlayer manifest={manifest} version={version} profile={profile} onProfileChange={setProfile} />
        ))}
      </main>
    </div>
  );
}
