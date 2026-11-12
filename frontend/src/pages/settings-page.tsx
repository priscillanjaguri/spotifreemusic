import { CheckCircle2, Loader2, Server } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { Logo } from "@/components/layout/logo";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { getApiBase, probeApiBase, setAccessToken, setApiBase } from "@/lib/config";
import { cn } from "@/lib/utils";

const FIELD =
  "h-12 rounded-2xl border-white/15 bg-white/5 px-4 text-[0.95rem] backdrop-blur-md focus-visible:bg-white/10";

type Props = {
  /** When true, this is the first-run gate (no back link required). */
  required?: boolean;
  onSaved?: (base: string) => void;
};

export function SettingsPage({ required = false, onSaved }: Props) {
  const [url, setUrl] = useState(() => getApiBase());
  const [status, setStatus] = useState<"idle" | "checking" | "ok" | "err">("idle");
  const [message, setMessage] = useState<string | null>(null);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setStatus("checking");
    setMessage(null);
    const result = await probeApiBase(url);
    if (!result.ok) {
      setStatus("err");
      setMessage(result.message);
      return;
    }
    const saved = setApiBase(url);
    // Changing servers invalidates any previous session token.
    setAccessToken(null);
    setStatus("ok");
    setMessage(result.message);
    onSaved?.(saved);
    if (!required) {
      // Full reload so auth + queries pick up the new origin cleanly.
      window.location.assign("/");
    } else {
      window.location.reload();
    }
  };

  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-lg flex-col justify-center gap-8 px-4 py-10">
      <div className="space-y-3 text-center">
        <Logo className="justify-center" />
        <h1 className="font-display text-3xl text-heading">Server URL</h1>
        <p className="text-sm text-subtle">
          The Android app talks to your Tunewise backend. Enter the host your phone can reach — a LAN IP on
          the same Wi‑Fi (e.g. <code className="text-cream">http://192.168.1.20:8741</code>) or a deployed
          HTTPS URL. Postgres, and R2 if you use it, must be reachable from that host.
        </p>
      </div>

      <form onSubmit={onSubmit} className="glass space-y-5 rounded-3xl p-6">
        <div className="space-y-2">
          <Label htmlFor="server-url">API base URL</Label>
          <div className="relative">
            <Server className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-subtle" />
            <Input
              id="server-url"
              className={cn(FIELD, "pl-10")}
              placeholder="http://192.168.x.x:8741"
              value={url}
              onChange={(e) => {
                setUrl(e.target.value);
                setStatus("idle");
                setMessage(null);
              }}
              autoCapitalize="off"
              autoCorrect="off"
              spellCheck={false}
              inputMode="url"
              required={required}
            />
          </div>
        </div>

        {message && (
          <Alert variant={status === "err" ? "destructive" : "default"}>
            {status === "ok" ? <CheckCircle2 /> : null}
            <AlertDescription>{message}</AlertDescription>
          </Alert>
        )}

        <Button type="submit" variant="cta" className="w-full" disabled={status === "checking"}>
          {status === "checking" ? (
            <>
              <Loader2 className="animate-spin" /> Checking…
            </>
          ) : (
            "Save & connect"
          )}
        </Button>
      </form>

      {!required && (
        <Link to="/" className={cn(buttonVariants({ variant: "ghost" }), "self-center")}>
          Back home
        </Link>
      )}
    </div>
  );
}
