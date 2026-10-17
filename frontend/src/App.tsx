/**
 * App.tsx — P5 root.
 *
 *   ?manifest=<id>   which manifest to play (default: the P2 golden fixture)
 *   ?locale= ?city=  profile overrides; ?profile=<url> loads a profile.json
 *   ?variants=1      the metric-3 variant grid + network ledger
 */

import { useEffect, useState } from 'react';
import { useManifest } from './hooks/useManifest';
import { BeatPlayer } from './components/BeatPlayer';
import { VariantGrid } from './components/VariantGrid';
import type { ViewerProfile } from './types/manifest';
import { DEFAULT_PROFILE } from './types/manifest';
import { loadProfile } from './runtime/profile';
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

  const params = new URLSearchParams(window.location.search);
  params.delete('variants');
  const playerHref = `?${params}`;
  params.set('variants', '1');
  const variantsHref = `?${params}`;

  return (
    <div className="app">
      <a className="skip-link" href="#main">Skip to player</a>
      <header className="app-header">
        <a className="brand" href={playerHref} aria-label="Vachan, player">
          <svg className="brand-mark" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M3 5h4.2L12 15.6 16.8 5H21l-7.4 15h-3.2z" />
          </svg>
          <span className="brand-name" translate="no">Vachan</span>
        </a>
        <p className="app-subtitle">
          {SHOW_VARIANTS ? 'One manifest, every viewer. Zero generation at play-time.' : 'Generated once, composed for each viewer.'}
        </p>
        <nav className="app-nav" aria-label="Views">
          <a href={playerHref} aria-current={SHOW_VARIANTS ? undefined : 'page'}>Player</a>
          <a href={variantsHref} aria-current={SHOW_VARIANTS ? 'page' : undefined}>Variants</a>
        </nav>
      </header>

      <main className="app-main" id="main" tabIndex={-1}>
        <h1 className="sr-only">{SHOW_VARIANTS ? 'Vachan variants' : 'Vachan player'}</h1>
        {loading && (
          <div className="state-skeleton" aria-busy="true" aria-label={`Loading manifest ${MANIFEST_ID}…`}>
            <div className="skeleton-stage" />
            <div className="skeleton-side" />
          </div>
        )}

        {error && (
          <div className="state-message state-error" role="alert">
            <strong>Couldn't load manifest <code>{MANIFEST_ID}</code>.</strong>
            <p>{error}</p>
            <p className="state-hint">Check the API is running: <code>uvicorn app.main:app --port 8080</code>.</p>
          </div>
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
