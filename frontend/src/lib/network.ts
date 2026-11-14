import { Capacitor } from "@capacitor/core";
import { Network } from "@capacitor/network";
import { useEffect, useState } from "react";

/** Best-effort online check (native Network plugin, else browser `navigator.onLine`). */
export async function isOnline(): Promise<boolean> {
  try {
    if (Capacitor.isNativePlatform()) {
      const status = await Network.getStatus();
      return status.connected;
    }
  } catch {
    /* fall through */
  }
  return typeof navigator === "undefined" ? true : navigator.onLine;
}

export function useOnlineStatus(): { online: boolean; ready: boolean } {
  const [online, setOnline] = useState(typeof navigator === "undefined" ? true : navigator.onLine);
  const [ready, setReady] = useState(!Capacitor.isNativePlatform());

  useEffect(() => {
    let cancelled = false;
    const sync = async () => {
      const next = await isOnline();
      if (!cancelled) {
        setOnline(next);
        setReady(true);
      }
    };
    void sync();

    const onBrowser = () => void sync();
    window.addEventListener("online", onBrowser);
    window.addEventListener("offline", onBrowser);

    let handle: { remove: () => Promise<void> } | undefined;
    if (Capacitor.isNativePlatform()) {
      void Network.addListener("networkStatusChange", (status) => {
        if (!cancelled) setOnline(status.connected);
      }).then((h) => {
        handle = h;
      });
    }

    return () => {
      cancelled = true;
      window.removeEventListener("online", onBrowser);
      window.removeEventListener("offline", onBrowser);
      void handle?.remove();
    };
  }, []);

  return { online, ready };
}

/** True when the WebView is serving the bundled shell (not the live Render origin). */
export function isLocalShell(): boolean {
  if (typeof window === "undefined") return false;
  const host = window.location.hostname;
  return host === "localhost" || host === "127.0.0.1" || host.endsWith(".localhost");
}
