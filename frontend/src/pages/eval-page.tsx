import { Activity, FlaskConical, Loader2, Play, RefreshCw, Sparkles } from "lucide-react";
import { useMemo, useState } from "react";
import { HairWaves, Petal, Rose } from "@/components/decor";
import { Logo } from "@/components/layout/logo";
import { EmptyState, ErrorState } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import {
  METRIC_ORDER,
  formatMetric,
  formatWhen,
  metricLabel,
  useEvalSnapshots,
  useEvalSummary,
  useRunEval,
  type EvalSnapshot,
} from "@/lib/eval";
import { cn } from "@/lib/utils";

function MetricCard({
  name,
  value,
  blurb,
  delay,
}: {
  name: string;
  value: number | undefined;
  blurb: string;
  delay: number;
}) {
  return (
    <article
      className="glass glass-inset animate-in fade-in slide-in-from-bottom-3 fill-mode-both rounded-[1.6rem] p-5"
      style={{ animationDelay: `${delay}ms`, animationDuration: "600ms" }}
    >
      <p className="text-sm font-semibold text-muted-foreground">{name}</p>
      <p className="mt-1 font-display text-4xl font-semibold tabular-nums text-heading">{formatMetric(value)}</p>
      <p className="mt-2 text-sm leading-relaxed text-subtle">{blurb}</p>
    </article>
  );
}

function TrendChart({ snapshots }: { snapshots: EvalSnapshot[] }) {
  const series = useMemo(() => {
    const chronological = [...snapshots].reverse();
    return chronological.map((s) => ({
      id: s.id,
      label: s.created_at
        ? new Date(s.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })
        : `#${s.id}`,
      precision: s.metrics.precision_at_k ?? 0,
      recall: s.metrics.recall_at_k ?? 0,
      diversity: s.metrics.diversity ?? 0,
      coverage: s.metrics.coverage ?? 0,
    }));
  }, [snapshots]);

  if (series.length === 0) {
    return (
      <p className="text-sm text-subtle">No snapshots yet — run an eval to start the trend line.</p>
    );
  }

  const w = 640;
  const h = 200;
  const pad = { t: 16, r: 12, b: 28, l: 36 };
  const innerW = w - pad.l - pad.r;
  const innerH = h - pad.t - pad.b;
  const maxY = Math.max(0.05, ...series.flatMap((p) => [p.precision, p.recall, p.diversity, p.coverage]));

  const xAt = (i: number) => pad.l + (series.length === 1 ? innerW / 2 : (i / (series.length - 1)) * innerW);
  const yAt = (v: number) => pad.t + innerH - (v / maxY) * innerH;

  const line = (key: "precision" | "recall" | "diversity" | "coverage") =>
    series.map((p, i) => `${i === 0 ? "M" : "L"} ${xAt(i).toFixed(1)} ${yAt(p[key]).toFixed(1)}`).join(" ");

  const lines = [
    { key: "precision" as const, stroke: "var(--color-orchid-glow)", label: "Precision" },
    { key: "recall" as const, stroke: "var(--color-wisteria)", label: "Recall" },
    { key: "diversity" as const, stroke: "var(--color-lavender)", label: "Diversity" },
    { key: "coverage" as const, stroke: "var(--color-heliotrope)", label: "Coverage" },
  ];

  return (
    <div>
      <svg viewBox={`0 0 ${w} ${h}`} className="h-auto w-full overflow-visible" role="img" aria-label="Eval metrics over time">
        {[0, 0.25, 0.5, 0.75, 1].map((t) => {
          const y = pad.t + innerH * (1 - t);
          return (
            <g key={t}>
              <line x1={pad.l} x2={w - pad.r} y1={y} y2={y} stroke="rgb(255 220 255 / 0.12)" strokeWidth={1} />
              <text x={pad.l - 8} y={y + 3} textAnchor="end" fill="rgb(201 192 212 / 0.7)" fontSize={10}>
                {Math.round(maxY * t * 100)}%
              </text>
            </g>
          );
        })}
        {lines.map((l, idx) => (
          <path
            key={l.key}
            d={line(l.key)}
            fill="none"
            stroke={l.stroke}
            strokeWidth={2.5}
            strokeLinecap="round"
            strokeLinejoin="round"
            className="animate-in fade-in"
            style={{ animationDelay: `${idx * 120}ms`, animationDuration: "700ms" }}
          />
        ))}
        {series.map((p, i) => (
          <text key={p.id} x={xAt(i)} y={h - 6} textAnchor="middle" fill="rgb(201 192 212 / 0.75)" fontSize={10}>
            {p.label}
          </text>
        ))}
      </svg>
      <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-xs font-semibold text-muted-foreground">
        {lines.map((l) => (
          <li key={l.key} className="inline-flex items-center gap-1.5">
            <span className="size-2.5 rounded-full" style={{ background: l.stroke }} />
            {l.label}
          </li>
        ))}
      </ul>
    </div>
  );
}

function VolumeRow({ volume }: { volume: Record<string, number> }) {
  const items = [
    { key: "listening_events", label: "Listens" },
    { key: "interactions", label: "Feedback" },
    { key: "users", label: "Users" },
    { key: "catalogue_songs", label: "Catalogue" },
    { key: "collection_saves", label: "Saves" },
  ];
  return (
    <dl className="grid grid-cols-2 gap-3 sm:grid-cols-5">
      {items.map((item) => (
        <div key={item.key} className="rounded-2xl bg-accent/40 px-3 py-3 text-center">
          <dt className="text-[11px] font-bold uppercase tracking-wide text-subtle">{item.label}</dt>
          <dd className="mt-1 font-display text-2xl font-semibold tabular-nums text-heading">
            {(volume[item.key] ?? 0).toLocaleString()}
          </dd>
        </div>
      ))}
    </dl>
  );
}

function FeedbackCounts({ counts }: { counts: Record<string, number> }) {
  const rows = [
    { key: "interested", label: "Liked" },
    { key: "not_interested", label: "Not interested" },
    { key: "saved", label: "Saved" },
    { key: "skipped", label: "Skipped" },
    { key: "dismissed", label: "Dismissed" },
    { key: "collection_saves", label: "Collection saves" },
  ];
  const max = Math.max(1, ...rows.map((r) => counts[r.key] ?? 0));
  return (
    <ul className="space-y-3">
      {rows.map((row) => {
        const n = counts[row.key] ?? 0;
        return (
          <li key={row.key}>
            <div className="flex justify-between gap-3 text-sm">
              <span className="font-semibold text-muted-foreground">{row.label}</span>
              <span className="tabular-nums text-subtle">{n.toLocaleString()}</span>
            </div>
            <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-accent">
              <div
                className="h-full rounded-full bg-gradient-to-r from-violet via-wisteria to-lavender transition-all duration-700"
                style={{ width: `${Math.max(n > 0 ? 6 : 0, (n / max) * 100)}%` }}
              />
            </div>
          </li>
        );
      })}
    </ul>
  );
}

export function EvalPage() {
  const summary = useEvalSummary();
  const snapshots = useEvalSnapshots();
  const run = useRunEval();
  const [secret, setSecret] = useState("");
  const [showSecret, setShowSecret] = useState(false);

  const latest = summary.data?.latest ?? null;
  const blurbs = summary.data?.metric_blurbs ?? {};
  const schedule = summary.data?.schedule;

  const onRun = () => {
    if (!secret.trim()) {
      setShowSecret(true);
      return;
    }
    run.mutate({ secret: secret.trim() });
  };

  return (
    <div className="relative min-h-dvh overflow-x-hidden">
      <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden" aria-hidden>
        <div className="absolute -left-24 top-10 size-72 animate-float rounded-full bg-amethyst/40 blur-3xl" />
        <div className="absolute right-0 top-40 size-80 animate-glow-pulse rounded-full bg-orchid/25 blur-3xl" />
        <div className="absolute bottom-20 left-1/3 size-64 rounded-full bg-heliotrope/20 blur-3xl" />
        <Rose className="absolute -right-6 top-24 size-36 opacity-40" />
        <Petal className="absolute left-8 top-[28rem] size-16 rotate-12 opacity-30" />
        <HairWaves className="absolute bottom-0 left-0 w-full opacity-40" />
      </div>

      <header className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 pb-2 pt-8 sm:px-6">
        <Logo />
        <Badge variant="secondary" className="glass border-0 px-3 py-1 text-xs font-semibold">
          Recommender eval
        </Badge>
      </header>

      <main className="mx-auto max-w-5xl space-y-8 px-4 pb-20 pt-6 sm:px-6">
        <section className="animate-in fade-in slide-in-from-bottom-2 duration-700">
          <p className="text-sm font-semibold uppercase tracking-[0.2em] text-lilac">Continuous offline metrics</p>
          <h1 className="mt-2 font-display text-4xl font-semibold leading-tight text-heading sm:text-5xl">
            How Spotifree ranks
          </h1>
          <p className="mt-3 max-w-2xl text-base leading-relaxed text-muted-foreground">
            Hold-out precision, recall, diversity, and coverage from listening + feedback already in the
            database. Testers stay on the APK — this page is for QH and interviewers.
          </p>
        </section>

        {summary.isLoading ? (
          <div className="grid gap-4 sm:grid-cols-2">
            <Skeleton className="h-36 rounded-[1.6rem]" />
            <Skeleton className="h-36 rounded-[1.6rem]" />
          </div>
        ) : summary.isError ? (
          <ErrorState error={summary.error} onRetry={() => void summary.refetch()} />
        ) : (
          <>
            <section className="glass glass-inset rounded-[1.75rem] p-5 sm:p-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <Activity className="size-4 text-orchid-glow" aria-hidden />
                    <h2 className="font-display text-2xl font-semibold text-heading">Last run</h2>
                    {latest && (
                      <Badge variant="outline" className="border-lilac/40 text-lilac">
                        {latest.source === "holdout" ? "Live hold-out" : "Synthetic fallback"}
                      </Badge>
                    )}
                  </div>
                  <p className="mt-1 text-sm text-subtle">
                    {latest ? formatWhen(latest.created_at) : "No snapshot stored yet"}
                    {latest ? ` · k=${latest.k}` : ""}
                    {schedule?.due ? " · due for another run" : ""}
                  </p>
                </div>
                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      void summary.refetch();
                      void snapshots.refetch();
                    }}
                  >
                    <RefreshCw className={cn("size-3.5", summary.isFetching && "animate-spin")} />
                    Refresh
                  </Button>
                  <Button type="button" variant="cta" size="sm" onClick={() => setShowSecret((v) => !v)}>
                    <Play className="size-3.5" />
                    Run now
                  </Button>
                </div>
              </div>

              {showSecret && (
                <div className="mt-4 space-y-3 rounded-2xl border border-glass-edge/20 bg-midnight/30 p-4">
                  <p className="text-sm text-muted-foreground">
                    Enter the server <code className="text-lilac">EVAL_RUN_SECRET</code>, then run. The secret
                    is sent only to the API and is not stored in this page.
                  </p>
                  <div className="flex flex-col gap-2 sm:flex-row">
                    <Input
                      type="password"
                      autoComplete="off"
                      placeholder="Eval run secret"
                      value={secret}
                      onChange={(e) => setSecret(e.target.value)}
                      className="sm:max-w-xs"
                    />
                    <Button type="button" variant="cta" disabled={run.isPending} onClick={onRun}>
                      {run.isPending ? <Loader2 className="size-4 animate-spin" /> : <FlaskConical className="size-4" />}
                      {run.isPending ? "Running…" : "Run eval"}
                    </Button>
                  </div>
                  {run.isError && <p className="text-sm text-rose">{(run.error as Error).message}</p>}
                  {run.isSuccess && <p className="text-sm text-orchid-glow">{run.data.message}</p>}
                </div>
              )}

              <div className="mt-5">
                {latest ? (
                  <VolumeRow volume={latest.data_volume} />
                ) : (
                  <EmptyState
                    icon={FlaskConical}
                    title="Waiting for the first snapshot"
                    description="Use Run now with EVAL_RUN_SECRET, or wait for the daily / volume schedule."
                  />
                )}
              </div>
            </section>

            {latest && (
              <section className="grid gap-4 sm:grid-cols-2">
                {METRIC_ORDER.map((key, i) => (
                  <MetricCard
                    key={key}
                    name={metricLabel(key)}
                    value={latest.metrics[key]}
                    blurb={blurbs[key] ?? ""}
                    delay={80 + i * 70}
                  />
                ))}
              </section>
            )}

            <section className="glass glass-inset rounded-[1.75rem] p-5 sm:p-6">
              <h2 className="font-display text-2xl font-semibold text-heading">Trend over time</h2>
              <p className="mt-1 text-sm text-subtle">Snapshots newest on the right after each successful run.</p>
              <div className="mt-5">
                {snapshots.isLoading ? (
                  <Skeleton className="h-48 w-full rounded-2xl" />
                ) : snapshots.isError ? (
                  <ErrorState error={snapshots.error} onRetry={() => void snapshots.refetch()} />
                ) : (
                  <TrendChart snapshots={snapshots.data?.items ?? []} />
                )}
              </div>
            </section>

            <section className="grid gap-4 lg:grid-cols-2">
              <article className="glass glass-inset rounded-[1.75rem] p-5 sm:p-6">
                <div className="flex items-center gap-2">
                  <Sparkles className="size-4 text-orchid-glow" aria-hidden />
                  <h2 className="font-display text-2xl font-semibold text-heading">How the model ranks</h2>
                </div>
                <p className="mt-3 text-sm leading-relaxed text-muted-foreground">
                  {summary.data?.ranking_blurb}
                </p>
                <ol className="mt-4 space-y-2 text-sm text-subtle">
                  <li>
                    <span className="font-semibold text-lilac">1. Features</span> — genres + audio traits become a
                    song vector.
                  </li>
                  <li>
                    <span className="font-semibold text-lilac">2. Cosine</span> — rank by similarity to the blended
                    short/long taste profile.
                  </li>
                  <li>
                    <span className="font-semibold text-lilac">3. MMR</span> — re-order for diversity, then a light
                    exploration nudge.
                  </li>
                </ol>
              </article>

              <article className="glass glass-inset rounded-[1.75rem] p-5 sm:p-6">
                <h2 className="font-display text-2xl font-semibold text-heading">Feedback (counts only)</h2>
                <p className="mt-1 text-sm text-subtle">Aggregates across users — no private song lists.</p>
                <div className="mt-4">
                  {latest ? (
                    <FeedbackCounts counts={latest.feedback_counts} />
                  ) : (
                    <p className="text-sm text-subtle">Counts appear after the first snapshot.</p>
                  )}
                </div>
              </article>
            </section>
          </>
        )}
      </main>
    </div>
  );
}
