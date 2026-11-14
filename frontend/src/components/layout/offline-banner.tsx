import { WifiOff } from "lucide-react";
import { isLocalShell, useOnlineStatus } from "@/lib/network";

/** Compact strip when the APK / browser has no network (cached library still works). */
export function OfflineBanner() {
  const { online, ready } = useOnlineStatus();
  if (!ready || online) return null;
  const local = isLocalShell();
  return (
    <div
      role="status"
      className="glass-soft relative z-50 flex items-center justify-center gap-2 border-b border-white/10 px-3 py-2 text-center text-xs font-semibold text-lavender"
    >
      <WifiOff className="size-3.5 shrink-0 text-orchid-glow" aria-hidden />
      <span>
        Offline{local ? " · local shell" : ""}. My Library plays from cache. Discover, lyrics, and Jamendo need
        network.
      </span>
    </div>
  );
}
