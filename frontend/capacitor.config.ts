import type { CapacitorConfig } from "@capacitor/cli";

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
