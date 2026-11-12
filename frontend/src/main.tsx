import { Capacitor } from "@capacitor/core";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { initNativeChrome } from "./lib/native";
import { registerServiceWorker } from "./lib/pwa";
import "./index.css";

void initNativeChrome();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

// Service worker is for the browser PWA only — skip inside the native WebView.
if (!Capacitor.isNativePlatform()) {
  registerServiceWorker();
}
