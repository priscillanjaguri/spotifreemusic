/* Tunewise service worker — installability + app-shell cache only.
 *
 * NEVER cache:
 *   - /api/* (auth cookies, private library, recommendations)
 *   - audio streams / Range responses / library media
 * Network-first for navigations; cache-first only for hashed build assets.
 */
const SHELL_CACHE = "tunewise-shell-v1";
const SHELL_URLS = ["/", "/manifest.webmanifest", "/favicon.svg", "/icon-192.png", "/icon-512.png"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(SHELL_CACHE)
      .then((cache) => cache.addAll(SHELL_URLS))
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== SHELL_CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

function isPrivateOrMedia(url) {
  const path = url.pathname;
  if (path.startsWith("/api/")) return true;
  if (path.includes("/stream") || path.includes("/cover") || path.includes("/mock-audio")) return true;
  if (/\.(mp3|m4a|aac|flac|ogg|oga|wav|webm)(\?|$)/i.test(path)) return true;
  return false;
}

function isShellAsset(url) {
  if (url.origin !== self.location.origin) return false;
  if (isPrivateOrMedia(url)) return false;
  // Vite hashed bundles + static icons
  if (url.pathname.startsWith("/assets/")) return true;
  if (/\.(js|css|svg|png|webmanifest|woff2?)$/i.test(url.pathname)) return true;
  return false;
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  let url;
  try {
    url = new URL(req.url);
  } catch {
    return;
  }

  // Never intercept API or audio — go straight to network, no cache.put.
  if (isPrivateOrMedia(url)) return;

  // App navigations: network first, fall back to cached shell.
  if (req.mode === "navigate") {
    event.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          if (res.ok) caches.open(SHELL_CACHE).then((c) => c.put("/", copy)).catch(() => undefined);
          return res;
        })
        .catch(() => caches.match("/") || caches.match(req)),
    );
    return;
  }

  // Static shell assets: cache-first.
  if (isShellAsset(url)) {
    event.respondWith(
      caches.match(req).then(
        (hit) =>
          hit ||
          fetch(req).then((res) => {
            if (res.ok) {
              const copy = res.clone();
              caches.open(SHELL_CACHE).then((c) => c.put(req, copy)).catch(() => undefined);
            }
            return res;
          }),
      ),
    );
  }
});
