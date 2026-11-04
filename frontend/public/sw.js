/* Only the static app shell is cached. Private /api responses are never cached. */
const CACHE = 'classpulse-learning-shell-v1';
const SHELL = ['/', '/index.html', '/manifest.webmanifest', '/favicon.svg'];
self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll(SHELL)));
  self.skipWaiting();
});
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET' || url.origin !== self.location.origin || url.pathname.startsWith('/api') || url.pathname.startsWith('/health')) return;
  if (event.request.mode === 'navigate') {
    event.respondWith(fetch(event.request).then(response => {
      if (response.ok) { const copy = response.clone(); event.waitUntil(caches.open(CACHE).then(cache => cache.put('/', copy))); }
      return response;
    }).catch(() => caches.match('/')));
  } else if (/\.(js|css|svg|woff2)$/.test(url.pathname)) {
    // Vite preview varies static files by Origin. Cache warmup has no Origin
    // header; same-origin static assets are identical for every requester.
    event.respondWith(caches.match(event.request, { ignoreVary: true }).then(cached => cached || fetch(event.request).then(response => {
      if (response.ok) { const copy = response.clone(); event.waitUntil(caches.open(CACHE).then(cache => cache.put(event.request, copy))); }
      return response;
    })));
  }
});
self.addEventListener('message', event => {
  if (event.data?.type !== 'CACHE_LEARNING_SHELL') return;
  const urls = (event.data.urls || []).slice(0, 120).filter(value => {
    try { const url = new URL(value); return url.origin === self.location.origin && url.pathname.startsWith('/assets/') && /\.(js|css|woff2)$/.test(url.pathname); }
    catch { return false; }
  });
  event.waitUntil(caches.open(CACHE).then(cache => cache.addAll([...SHELL, ...urls])).then(() => event.ports[0]?.postMessage({ ready: true })).catch(() => event.ports[0]?.postMessage({ ready: false })));
});
