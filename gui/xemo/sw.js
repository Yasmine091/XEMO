const CACHE = "xemo-static-v999";
const SHELL = ["/", "/xemo/css/app.css?v=35", "/xemo/js/app-runtime-947.js?v=1115", "/xemo/js/movement-library.js?v=2", "/xemo/js/perception.js?v=7", "/xemo/js/perception-worker.js?v=4", "/xemo/js/protocol.js?v=98", "/xemo/fonts/SF-Pixelate.ttf", "/xemo/manifest.webmanifest"];
self.addEventListener("install", event => event.waitUntil(caches.open(CACHE).then(async cache => {
  await Promise.all(SHELL.map(async url => { try { const r = await fetch(url, {cache:"no-cache"}); if (r.ok) await cache.put(url, r); } catch (_) {} }));
  await self.skipWaiting();
})));
self.addEventListener("activate", event => event.waitUntil(Promise.all([caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE && /^xemo-static-/i.test(key)).map(key => caches.delete(key)))), self.clients.claim()])));
self.addEventListener("fetch", event => {
  if (event.request.method !== "GET" || new URL(event.request.url).pathname.startsWith("/api/")) return;
  event.respondWith(fetch(event.request).then(response => {
    if (response.ok) {
      const copy = response.clone();
      caches.open(CACHE).then(cache => cache.put(event.request, copy));
    }
    return response;
  }).catch(() => {
    const url = new URL(event.request.url);
    return caches.match(event.request).then(hit => hit || caches.match(url.pathname));
  }));
});
