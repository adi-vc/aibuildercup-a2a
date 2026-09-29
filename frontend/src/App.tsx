/**
 * App.tsx — P0 root component.
 *
 * Loads the p0_single_beat fixture manifest and renders the BeatPlayer.
 * The manifest ID can be overridden via the ?manifest= query param so
 * teammates can test different fixtures without a code change.
 */

import { useState } from 'react';
import { useManifest } from './hooks/useManifest';
import { BeatPlayer } from './components/BeatPlayer';
import type { ViewerProfile } from './types/manifest';
import { DEFAULT_PROFILE } from './types/manifest';
import './App.css';

// Read manifest id from query param; default to the P0 fixture.
const urlParams = new URLSearchParams(window.location.search);
const MANIFEST_ID = urlParams.get('manifest') ?? 'p0_single_beat';

export default function App() {
  const { manifest, loading, error } = useManifest(MANIFEST_ID);
  const [profile, setProfile] = useState<ViewerProfile>(DEFAULT_PROFILE);

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title">Vachan <span className="app-phase">· P0</span></h1>
        <p className="app-subtitle">Walking skeleton — manifest renders in browser ✓</p>
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

        {manifest && (
          <BeatPlayer
            manifest={manifest}
            profile={profile}
            onProfileChange={setProfile}
          />
        )}
      </main>
    </div>
  );
}
