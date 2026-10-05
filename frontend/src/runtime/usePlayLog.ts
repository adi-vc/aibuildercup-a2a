/**
 * usePlayLog — feeds the PlayRecorder from the live player and submits it.
 *
 * One recorder per manifest version for the whole session: a locale or city
 * swap is a new *segment* of the same play, never a new play (that is the
 * moment the receipt exists to capture). The profile hash is taken from the
 * profile the play started with.
 *
 * submit() ends the current play, returns the server-signed record, and
 * starts the next play from the current screen. On page hide an unsent play
 * is flushed with a keepalive request, so closing the tab still leaves one.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { submitPlay } from '../api/client';
import type { Manifest, ViewerProfile } from '../types/manifest';
import type { BindingResolution } from './bindings';
import { PlayRecorder, profileHash, type SignedPlayRecord } from './playlog';

export function usePlayLog(
  manifest: Manifest, version: string, profile: ViewerProfile, bindings: Record<string, BindingResolution>,
) {
  const [beatId, setBeatId] = useState<string | null>(null);
  const recorderRef = useRef<PlayRecorder | null>(null);
  const startHashRef = useRef<string>('h_pending');

  useEffect(() => {
    recorderRef.current = new PlayRecorder(manifest, version);
  }, [manifest, version]);

  const observe = useCallback(() => {
    const recorder = recorderRef.current;
    if (!recorder || !beatId) return;
    if (recorder.observe(beatId, profile.locale, profile.city, bindings)) {
      // A play just began: pin the profile it began with.
      profileHash(profile).then((h) => { startHashRef.current = h; }, () => undefined);
    }
  }, [beatId, profile, bindings]);

  useEffect(observe, [observe]);

  useEffect(() => {
    const flush = () => {
      const record = recorderRef.current?.build(startHashRef.current);
      if (!record) return;
      recorderRef.current?.reset();
      submitPlay(record, { keepalive: true }).catch(() => undefined);
    };
    const onHide = () => document.visibilityState === 'hidden' && flush();
    window.addEventListener('pagehide', flush);
    document.addEventListener('visibilitychange', onHide);
    return () => {
      window.removeEventListener('pagehide', flush);
      document.removeEventListener('visibilitychange', onHide);
    };
  }, []);

  const submit = useCallback(async (): Promise<SignedPlayRecord | null> => {
    const record = recorderRef.current?.build(startHashRef.current);
    if (!record) return null;
    recorderRef.current?.reset();
    observe(); // the next play opens on the current screen
    return submitPlay(record);
  }, [observe]);

  return { onBeatChange: setBeatId, submit };
}
