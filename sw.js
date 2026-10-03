// MjrFts v7 — al subir una versión nueva, cambia el número de CACHE
const CACHE = 'mjrfts-v7';
const CORE = ['./', './index.html', './manifest.webmanifest', './icon-192.png', './icon-512.png'];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(CORE)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== location.origin) return;
  if (req.mode === 'navigate') {
    // Intenta la versión nueva hasta 3 segundos; si la señal no da, abre la copia guardada
    const red = fetch(req).then(r => { const c = r.clone(); caches.open(CACHE).then(x => x.put('./index.html', c)); return r; });
    const espera = new Promise(res => setTimeout(res, 3000)).then(() => caches.match('./index.html'));
    e.respondWith(Promise.race([red.catch(() => caches.match('./index.html')), espera.then(r => r || red)]));
    return;
  }
  e.respondWith(caches.match(req).then(hit => hit || fetch(req)));
});
