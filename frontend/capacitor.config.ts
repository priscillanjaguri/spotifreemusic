import type { CapacitorConfig } from "@capacitor/cli";

/**
 * Capacitor loads the bundled Vite `dist/` assets (not a remote SPA).
 * Production API origin is baked via `frontend/.env.production` → `VITE_API_BASE_URL`
 * (https://spotifree-rw0a.onrender.com). Users can still override in-app Server URL.
 */
const config: CapacitorConfig = {
  appId: "com.spotifree.app",
  appName: "Spotifree",
  webDir: "dist",
  server: {
    // Allow http:// LAN API hosts from the WebView (debug / sideload builds).
    cleartext: true,
    androidScheme: "https",
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
