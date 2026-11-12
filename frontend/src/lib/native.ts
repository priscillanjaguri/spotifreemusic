import { Capacitor } from "@capacitor/core";
import { StatusBar, Style } from "@capacitor/status-bar";

/** Deep purple status bar to match Tunewise chrome. */
export async function initNativeChrome(): Promise<void> {
  if (!Capacitor.isNativePlatform()) return;
  try {
    await StatusBar.setStyle({ style: Style.Dark });
    await StatusBar.setBackgroundColor({ color: "#2a0a3d" });
  } catch {
    /* StatusBar plugin unavailable in browser / unsupported platforms */
  }
}
