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
  const { manifest, loading, error } = useManifest(MANIFEST_ID);
  const [profile, setProfile] = useState<ViewerProfile>(DEFAULT_PROFILE);

  useEffect(() => {
    loadProfile(window.location.search).then(setProfile);
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title">Vachan <span className="app-phase">· P5</span></h1>
        <p className="app-subtitle">
          {SHOW_VARIANTS ? 'One manifest, every viewer — zero generation at play-time' : 'Generated once, composed per viewer'}
        </p>
      </header>

      <main className="app-main">
        {loading && (
          <div className="state-message">
            Loading manifest <code>{MANIFEST_ID}</code>…
          </div>
        )}

        {error && (
          <div className="state-message state-error">
            <strong>Error:</strong> {error}
            <br />
            <small>Is the API running? (<code>docker compose up</code> or <code>uvicorn app.main:app</code>)</small>
          </div>
        )}

        {manifest && (SHOW_VARIANTS ? (
          <VariantGrid manifest={manifest} />
        ) : (
          <BeatPlayer manifest={manifest} profile={profile} onProfileChange={setProfile} />
        ))}
      </main>
    </div>
  );
}
