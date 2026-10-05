/**
 * sw.js — the C4 browser cache tier (vachan-plan.md §49).
 *
 *   /assets/*          cache-first   hashed bundles + Vault assets are immutable
 *   /v1/manifest/*     network-first fresh on every play (ETag makes it a 304);
 *                                    the cached copy plays offline or on a dead API
 *   everything else    network       incl. POST /v1/bindings/resolve — live values
 *                                    are never served from this cache
 */

const CACHE = 'vachan-c4-v1';

self.addEventListener('install', () => self.skipWaiting());

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k.startsWith('vachan-') && k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

async function cacheFirst(request) {
  const cache = await caches.open(CACHE);
  const hit = await cache.match(request);
  if (hit) return hit;
  const response = await fetch(request);
  if (response.ok) cache.put(request, response.clone());
  return response;
}

async function networkFirst(request) {
  const cache = await caches.open(CACHE);
  try {
    const response = await fetch(request);
    if (response.ok) cache.put(request, response.clone());
    return response;
  } catch (err) {
    const hit = await cache.match(request);
    if (hit) return hit;
    throw err;
  }
}

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.pathname.startsWith('/v1/manifest/')) {
    event.respondWith(networkFirst(request));
  } else if (url.origin === self.location.origin && url.pathname.startsWith('/assets/')) {
    event.respondWith(cacheFirst(request));
  }
});
