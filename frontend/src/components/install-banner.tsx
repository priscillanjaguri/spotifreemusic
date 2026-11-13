import { Download, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";

type BeforeInstallPromptEvent = Event & {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
};

/** Soft “Install Spotifree” chip when Chrome fires beforeinstallprompt (Android). */
export function InstallBanner() {
  const [deferred, setDeferred] = useState<BeforeInstallPromptEvent | null>(null);
  const [hidden, setHidden] = useState(() => localStorage.getItem("tw-install-dismissed") === "1");

  useEffect(() => {
    const onPrompt = (e: Event) => {
      e.preventDefault();
      setDeferred(e as BeforeInstallPromptEvent);
    };
    window.addEventListener("beforeinstallprompt", onPrompt);
    return () => window.removeEventListener("beforeinstallprompt", onPrompt);
  }, []);

  if (hidden || !deferred) return null;

  return (
    <div className="glass-strong glass-edge fixed inset-x-3 top-3 z-50 flex items-center gap-3 rounded-2xl p-3 shadow-whip-lg lg:left-auto lg:right-6 lg:w-[22rem]">
      <div className="min-w-0 flex-1">
        <p className="text-sm font-bold text-heading">Install Spotifree</p>
        <p className="text-xs text-muted-foreground">Add to your home screen for full-screen play & uploads.</p>
      </div>
      <Button
        size="sm"
        variant="cta"
        onClick={async () => {
          await deferred.prompt();
          setDeferred(null);
        }}
      >
        <Download data-icon="inline-start" /> Install
      </Button>
      <Button
        size="icon-sm"
        variant="ghost"
        aria-label="Dismiss"
        onClick={() => {
          localStorage.setItem("tw-install-dismissed", "1");
          setHidden(true);
        }}
      >
        <X />
      </Button>
    </div>
  );
}
