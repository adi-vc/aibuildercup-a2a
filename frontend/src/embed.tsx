/**
 * embed.tsx — entry for the chromeless embed page (embed.html), loaded inside
 * a host's <iframe>. Separate from main.tsx so the embed bundle carries only
 * the player, not the studio views.
 */

import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { EmbedApp } from './components/EmbedApp';
import { registerServiceWorker } from './runtime/serviceWorker';
import './embed.css';

registerServiceWorker();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <EmbedApp />
  </StrictMode>,
);
