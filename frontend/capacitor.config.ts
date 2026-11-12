import type { CapacitorConfig } from "@capacitor/cli";

const config: CapacitorConfig = {
  appId: "com.tunewise.app",
  appName: "Tunewise",
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
