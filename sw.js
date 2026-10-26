// Offline support. Online: always fetch fresh files (and keep a copy).
// Offline: serve the last copy. Only this site's own files are cached, never other sites or the vote server.
const CACHE = "will-it-launch-v2";
const CORE = [
  "./", "index.html", "styles.css", "theme.js", "app.js", "config.js", "data/games.js", "data/anticheats.js", "manifest.webmanifest",
  "fonts/fonts.css", "fonts/figtree-latin.woff2", "fonts/rubik-latin.woff2", "icons/icon-192.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE).then((c) => c.addAll(CORE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  const url = new URL(req.url);
  if (req.method !== "GET" || url.origin !== self.location.origin) return;
  event.respondWith(
    fetch(req)
      .then((res) => {
        if (res.ok && !url.search) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
        }
        return res;
      })
      // Offline and not cached: pages fall back to the app shell; other files just fail.
      .catch(() => caches.match(req, { ignoreSearch: true })
        .then((hit) => hit || (req.mode === "navigate" ? caches.match("index.html") : Response.error()))),
  );
});
