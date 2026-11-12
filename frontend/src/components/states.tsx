import { AlertTriangle, PlugZap, RotateCw, WifiOff, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { Petal } from "@/components/decor";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";

type EmptyStateProps = {
  icon: LucideIcon;
  title: string;
  description: ReactNode;
  action?: ReactNode;
  className?: string;
  tone?: "lavender" | "orchid" | "rose";
};

const TONES = {
  lavender: "from-violet-sheen to-amethyst-shadow text-cream",
  orchid: "from-mauve/80 via-amethyst to-royal-purple-shadow text-cream",
  rose: "from-rose/70 to-amethyst-shadow text-cream",
};

export function EmptyState({ icon: Icon, title, description, action, className, tone = "lavender" }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "powder glass glass-inset relative flex flex-col items-center justify-center overflow-hidden rounded-[1.75rem] px-6 py-14 text-center",
        className,
      )}
    >
      <Petal className="absolute top-6 left-[12%] size-6 rotate-[-25deg] opacity-60" />
      <Petal className="absolute right-[10%] bottom-8 size-8 rotate-[140deg] opacity-50" />
      <div className={cn("gloss mb-5 grid size-16 place-items-center rounded-full bg-gradient-to-br ring-1 ring-lavender/20 shadow-polish", TONES[tone])}>
        <Icon className="size-7" aria-hidden />
      </div>
      <h3 className="font-display text-2xl font-semibold text-heading">{title}</h3>
      <div className="mt-2 max-w-md text-sm leading-relaxed text-muted-foreground">{description}</div>
      {action && <div className="mt-6 flex flex-wrap justify-center gap-2">{action}</div>}
    </div>
  );
}

export function ErrorState({ error, onRetry, className }: { error: unknown; onRetry?: () => void; className?: string }) {
  const offline = error instanceof ApiError && error.status === 0;
  const message = error instanceof Error ? error.message : "Something unexpected happened.";
  return (
    <EmptyState
      tone="rose"
      icon={offline ? WifiOff : AlertTriangle}
      title={offline ? "You're offline" : "That didn't load"}
      description={message}
      className={className}
      action={
        onRetry && (
          <Button variant="outline" onClick={onRetry}>
            <RotateCw data-icon="inline-start" /> Try again
          </Button>
        )
      }
    />
  );
}

export function ProviderNotConfigured({ message, className }: { message: string; className?: string }) {
  return (
    <EmptyState
      tone="orchid"
      icon={PlugZap}
      title="Music search isn't switched on yet"
      className={className}
      description={
        <>
          <p>{message}</p>
          <p className="mt-3 text-xs text-subtle">
            Get a free client ID at{" "}
            <a
              className="font-semibold text-accent-foreground underline-offset-4 hover:underline"
              href="https://developer.jamendo.com"
              target="_blank"
              rel="noreferrer"
            >
              developer.jamendo.com
            </a>
            , add <code className="rounded-md bg-accent px-1.5 py-0.5 text-accent-foreground">JAMENDO_CLIENT_ID</code> to{" "}
            <code className="rounded-md bg-accent px-1.5 py-0.5 text-accent-foreground">.env</code>, and restart the API. Your
            collection keeps working in the meantime.
          </p>
        </>
      }
    />
  );
}

export function SongListSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div className="glass glass-inset divide-y divide-white/10 overflow-hidden rounded-[1.75rem]" aria-busy aria-label="Loading">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex items-center gap-3 px-3 py-3 sm:px-4">
          <Skeleton className="size-11 rounded-xl bg-accent" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-3.5 w-2/5 bg-accent" />
            <Skeleton className="h-3 w-1/4 bg-muted" />
          </div>
          <Skeleton className="hidden h-3 w-24 bg-muted md:block" />
          <Skeleton className="size-8 rounded-full bg-accent" />
        </div>
      ))}
    </div>
  );
}
