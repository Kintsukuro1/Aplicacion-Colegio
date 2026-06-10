const APP_VERSION = "2026-06-01-offline-fix";
const CACHE_PREFIX = "sistema-escolar";
const STATIC_CACHE = `${CACHE_PREFIX}-static-${APP_VERSION}`;
const PAGES_CACHE = `${CACHE_PREFIX}-pages-${APP_VERSION}`;
const OFFLINE_URL = "/static/offline.html";
const CORE_PRECACHE_URLS = [
  OFFLINE_URL,
];

const OPTIONAL_PRECACHE_URLS = [
  "/",
  "/static/manifest.webmanifest",
  "/static/js/ui-system.js",
  "/static/css/design-system.css",
  "/static/css/components.css",
  "/static/css/index.css",
  "/static/img/pwa/icon-192.svg",
  "/static/img/pwa/icon-512.svg"
];

function isApiRequest(request) {
  const url = new URL(request.url);
  return url.pathname.startsWith("/api/");
}

function isDynamicOrPrivateRequest(request) {
  const url = new URL(request.url);
  const path = url.pathname;
  return (
    path.startsWith("/accounts/") ||
    path.startsWith("/dashboard/") ||
    path.startsWith("/admin/") ||
    path.startsWith("/api/") ||
    path.startsWith("/seleccionar-escuela/") ||
    path.startsWith("/entrar-escuela/") ||
    path.startsWith("/importar-datos/") ||
    path.startsWith("/gestionar-") ||
    path.startsWith("/setup/")
  );
}

function isSameOrigin(request) {
  const url = new URL(request.url);
  return url.origin === self.location.origin;
}

function isStaticRequest(request) {
  const url = new URL(request.url);
  return isSameOrigin(request) && url.pathname.startsWith("/static/");
}

function cleanupOldCaches() {
  return caches.keys().then((keys) =>
    Promise.all(
      keys
        .filter((key) => key.startsWith(`${CACHE_PREFIX}-`) && key !== STATIC_CACHE && key !== PAGES_CACHE)
        .map((key) => caches.delete(key))
    )
  );
}

function withTimeout(promise, ms) {
  return new Promise((resolve, reject) => {
    const timeoutId = setTimeout(() => reject(new Error("network-timeout")), ms);
    promise
      .then((value) => {
        clearTimeout(timeoutId);
        resolve(value);
      })
      .catch((error) => {
        clearTimeout(timeoutId);
        reject(error);
      });
  });
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(STATIC_CACHE)
      .then(async (cache) => {
        // Offline fallback must be present even if some optional assets fail.
        await Promise.all(CORE_PRECACHE_URLS.map((url) => cache.add(url)));
        await Promise.allSettled(OPTIONAL_PRECACHE_URLS.map((url) => cache.add(url)));
      })
      .catch(() => Promise.resolve())
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(cleanupOldCaches());
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") {
    return;
  }

  if (isDynamicOrPrivateRequest(request)) {
    // Dashboard/cuentas: red primero; offline solo si falla la red (no por 500 ni lentitud).
    if (request.mode === "navigate") {
      event.respondWith(
        fetch(request)
          .then((response) => response)
          .catch(async () => {
            const offlinePage = await caches.match(OFFLINE_URL);
            return offlinePage || Response.error();
          })
      );
    }
    return;
  }

  if (request.mode === "navigate") {
    event.respondWith(
      withTimeout(fetch(request), 4500)
        .then((response) => {
          if (response && response.status === 200) {
            const responseClone = response.clone();
            caches.open(PAGES_CACHE).then((cache) => cache.put(request, responseClone));
          }
          return response;
        })
        .catch(async () => {
          const cachedPage = await caches.match(request, { ignoreSearch: true });
          if (cachedPage) {
            return cachedPage;
          }
          const offlinePage = await caches.match(OFFLINE_URL);
          return offlinePage || caches.match("/");
        })
    );
    return;
  }

  if (isStaticRequest(request)) {
    event.respondWith(
      caches.match(request).then((cached) => {
        const networkFetch = fetch(request)
          .then((response) => {
            if (!response || response.status !== 200 || response.type !== "basic") {
              return response;
            }
            const responseClone = response.clone();
            caches.open(STATIC_CACHE).then((cache) => cache.put(request, responseClone));
            return response;
          })
          .catch(() => cached);

        return cached || networkFetch;
      })
    );
    return;
  }

  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) {
        return cached;
      }
      return fetch(request)
        .then((response) => {
          if (!response || response.status !== 200 || response.type !== "basic") {
            return response;
          }
          const responseClone = response.clone();
          caches.open(PAGES_CACHE).then((cache) => cache.put(request, responseClone));
          return response;
        })
        .catch(() => caches.match(OFFLINE_URL));
    })
  );
});
