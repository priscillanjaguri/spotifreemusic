/** Register the Tunewise service worker (shell cache only — never private audio). */
export function registerServiceWorker() {
  if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;

  const register = () => {
    navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch((err) => {
      console.warn("Tunewise SW registration failed", err);
    });
  };

  if (document.readyState === "complete") register();
  else window.addEventListener("load", register);
}
