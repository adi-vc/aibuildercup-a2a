/**
 * EmbedApp.tsx — the player as a host page sees it: no chrome, just the video.
 * Profile comes from the snippet's query string (?manifest=&city=&locale=).
 * A failure shows a quiet message inside the frame; it never breaks the host.
 */

import { useEffect, useState } from 'react';
import { useManifest } from '../hooks/useManifest';
import { loadProfile } from '../runtime/profile';
import { useBindings } from '../runtime/useBindings';
import type { Manifest, ViewerProfile } from '../types/manifest';
import { DEFAULT_PROFILE } from '../types/manifest';
import { RuntimePlayer } from './RuntimePlayer';

const params = new URLSearchParams(window.location.search);
const MANIFEST_ID = params.get('manifest') ?? '';

function EmbedPlayer({ manifest, profile }: { manifest: Manifest; profile: ViewerProfile }) {
  const bindings = useBindings(manifest, profile.city, profile.locale);
  return (
    <RuntimePlayer
      manifest={manifest}
      locale={profile.locale}
      bindings={bindings}
      entryBeat={profile.entry_beat}
      autoPlay
      style={{ height: '100%' }}
    />
  );
}

export function EmbedApp() {
  const { manifest, error } = useManifest(MANIFEST_ID);
  const [profile, setProfile] = useState<ViewerProfile | null>(null);

  useEffect(() => {
    loadProfile(window.location.search).then(setProfile, () => setProfile(DEFAULT_PROFILE));
  }, []);

  if (error || !MANIFEST_ID) return <div className="embed-message">This video is unavailable.</div>;
  if (!manifest || !profile || manifest.beats.length === 0) return <div className="embed-message" aria-busy="true" />;
  return <EmbedPlayer manifest={manifest} profile={profile} />;
}
