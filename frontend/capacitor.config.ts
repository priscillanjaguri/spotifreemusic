import type { CapacitorConfig } from "@capacitor/cli";

/**
 * Hybrid online/offline WebView:
 * - Online: load live SPA from Render (`server.url`) so UI updates without APK reinstall.
 * - Offline / Render unreachable: `errorPath` + MainActivity fall back to bundled `dist/` shell.
 * - My Library audio/metadata cache uses Filesystem + Preferences (see `src/lib/offline-library.ts`).
 *
 * Production API origin matches the hosted host (`VITE_API_BASE_URL` / `DEFAULT_HOSTED_API_BASE`).
 */
const LIVE_UI_ORIGIN = "https://spotifree-rw0a.onrender.com";

const config: CapacitorConfig = {
  appId: "com.spotifree.app",
  appName: "Spotifree",
  webDir: "dist",
  server: {
    url: LIVE_UI_ORIGIN,
    // Bundled SPA shown when `server.url` cannot load (no network / Render down).
    errorPath: "index.html",
    // Allow http:// LAN API hosts from the WebView (in-app Server URL overrides).
    cleartext: true,
    androidScheme: "https",
    // Keep SPA navigations on the hosted origin (and subpaths).
    allowNavigation: ["spotifree-rw0a.onrender.com"],
  },
  android: {
    allowMixedContent: true,
  },
  plugins: {
    StatusBar: {
      style: "DARK",
      backgroundColor: "#2a0a3d",
    },
  },
};

export default config;
