/**
 * serviceWorker.ts — register the C4 cache (public/sw.js) in production builds.
 * Dev is excluded so Vite's module graph is never served from a stale cache.
 * Registration failures (privacy modes, partitioned third-party frames) are
 * non-fatal: the player simply runs uncached.
 */

export function registerServiceWorker(): void {
  if (!import.meta.env.PROD || !('serviceWorker' in navigator)) return;
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js', { scope: '/' }).catch(() => undefined);
  });
}
