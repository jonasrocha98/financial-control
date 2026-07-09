// Service worker simples: cache do shell estático para uso offline básico.
const CACHE = "cf-v1";
const ASSETS = ["/static/css/style.css", "/static/manifest.json"];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(ASSETS)));
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  // Não cacheia POST nem requisições de navegação (sempre rede para dados frescos).
  if (request.method !== "GET") return;
  if (request.mode === "navigate") return;
  event.respondWith(
    caches.match(request).then((cached) => cached || fetch(request))
  );
});
