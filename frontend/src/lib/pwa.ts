/** Register the Spotifree service worker (shell cache only — never private audio). */
export function registerServiceWorker() {
  if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;

  const register = () => {
    navigator.serviceWorker
      .register("/sw.js", { scope: "/" })
      .then((reg) => {
        // Pick up new shell caches after Render deploys without waiting for a full reopen.
        void reg.update();
        reg.addEventListener("updatefound", () => {
          const worker = reg.installing;
          if (!worker) return;
          worker.addEventListener("statechange", () => {
            if (worker.state === "activated" && navigator.serviceWorker.controller) {
              // New SW claimed — soft-reload once so index.html points at fresh hashed assets.
              const key = "spotifree_sw_reload";
              if (!sessionStorage.getItem(key)) {
                sessionStorage.setItem(key, "1");
                window.location.reload();
              }
            }
          });
        });
      })
      .catch((err) => {
        console.warn("Spotifree SW registration failed", err);
      });
  };

  if (document.readyState === "complete") register();
  else window.addEventListener("load", register);
}
