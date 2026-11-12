import { AlertTriangle, PlugZap, RotateCw, WifiOff, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
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
  tone?: "violet" | "plum" | "berry";
};

const TONES = {
  violet: "from-amethyst/30 to-iris/10 text-lavender ring-amethyst/30",
  plum: "from-orchid/30 to-plum/10 text-magenta ring-orchid/30",
  berry: "from-berry/25 to-plum/10 text-berry ring-berry/30",
};

export function EmptyState({ icon: Icon, title, description, action, className, tone = "violet" }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center rounded-2xl border border-dashed border-heather bg-aubergine/50 px-6 py-14 text-center",
        className,
      )}
    >
      <div className={cn("mb-4 grid size-14 place-items-center rounded-2xl bg-gradient-to-br ring-1", TONES[tone])}>
        <Icon className="size-6" aria-hidden />
      </div>
      <h3 className="text-lg font-semibold text-lilac">{title}</h3>
      <div className="mt-1.5 max-w-md text-sm text-muted-foreground">{description}</div>
      {action && <div className="mt-6 flex flex-wrap justify-center gap-2">{action}</div>}
    </div>
  );
}

export function ErrorState({ error, onRetry, className }: { error: unknown; onRetry?: () => void; className?: string }) {
  const offline = error instanceof ApiError && error.status === 0;
  const message = error instanceof Error ? error.message : "Something unexpected happened.";
  return (
    <EmptyState
      tone="berry"
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
      tone="plum"
      icon={PlugZap}
      title="Music search isn't switched on yet"
      className={className}
      description={
        <>
          <p>{message}</p>
          <p className="mt-3 text-xs text-dusk">
            Get a free client ID at{" "}
            <a
              className="text-lavender underline-offset-4 hover:underline"
              href="https://developer.jamendo.com"
              target="_blank"
              rel="noreferrer"
            >
              developer.jamendo.com
            </a>
            , add <code className="rounded bg-eggplant px-1.5 py-0.5 text-lilac">JAMENDO_CLIENT_ID</code> to{" "}
            <code className="rounded bg-eggplant px-1.5 py-0.5 text-lilac">.env</code>, and restart the API. Your
            collection keeps working in the meantime.
          </p>
        </>
      }
    />
  );
}

export function SongListSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div className="divide-y divide-border/60 overflow-hidden rounded-2xl border bg-card/60" aria-busy aria-label="Loading">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex items-center gap-3 px-3 py-3 sm:px-4">
          <Skeleton className="size-11 rounded-lg bg-eggplant" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-3.5 w-2/5 bg-eggplant" />
            <Skeleton className="h-3 w-1/4 bg-eggplant/70" />
          </div>
          <Skeleton className="hidden h-3 w-24 bg-eggplant/70 md:block" />
          <Skeleton className="size-8 rounded-full bg-eggplant" />
        </div>
      ))}
    </div>
  );
}
