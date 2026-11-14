import type { CapacitorConfig } from "@capacitor/cli";

/**
 * Capacitor WebView loads the live SPA from Render (not bundled `dist/` as the primary UI).
 * Frontend/UI deploys via Render — no APK reinstall for web-only changes.
 * Native plugins (Capawesome FilePicker, StatusBar, etc.) still bridge into this WebView.
 *
 * Production API origin matches the same host (`VITE_API_BASE_URL` / `DEFAULT_HOSTED_API_BASE`).
 * Users can still override in-app Server URL (LAN http allowed via cleartext).
 */
const LIVE_UI_ORIGIN = "https://spotifree-rw0a.onrender.com";

const config: CapacitorConfig = {
  appId: "com.spotifree.app",
  appName: "Spotifree",
  webDir: "dist",
  server: {
    url: LIVE_UI_ORIGIN,
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
