import { BarChart3, Clock3, Disc3, HeartHandshake, Mic2, Sparkles, Trash2 } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { HairWaves, Petal, Rose } from "@/components/decor";
import { PageHeader } from "@/components/layout/app-shell";
import { CoverArt } from "@/components/music/cover-art";
import { SongRow } from "@/components/music/song-row";
import { EmptyState, ErrorState } from "@/components/states";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useAnalytics,
  useDeleteListeningHistory,
  useMemoryLane,
  usePreferences,
  useTasteTimeline,
  useUpdatePreferences,
} from "@/lib/analytics";
import { artistNames, formatTotalDuration, relativeDate } from "@/lib/format";
import { usePlayer } from "@/lib/player";
import type { AnalyticsPeriod, MemoryLaneItem, NamedCount } from "@/lib/types";
import { cn } from "@/lib/utils";

function formatRange(start: string, end: string) {
  const opts: Intl.DateTimeFormatOptions = { month: "short", day: "numeric" };
  const s = new Date(start + "T12:00:00");
  const e = new Date(end + "T12:00:00");
  return `${s.toLocaleDateString(undefined, opts)} – ${e.toLocaleDateString(undefined, opts)}`;
}

function StatTile({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="glass glass-inset rounded-[1.6rem] p-4 sm:p-5">
      <p className="text-sm font-semibold text-muted-foreground">{label}</p>
      <p className="mt-1 font-display text-3xl font-semibold text-heading sm:text-4xl">{value}</p>
      {hint && <p className="mt-1 text-xs text-subtle">{hint}</p>}
    </div>
  );
}

function RankBars({ title, rows, empty }: { title: string; rows: NamedCount[]; empty: string }) {
  const max = rows[0]?.listened_ms || 1;
  return (
    <section className="glass glass-inset rounded-[1.75rem] p-5">
      <h2 className="font-display text-2xl font-semibold text-heading">{title}</h2>
      {rows.length === 0 ? (
        <p className="mt-3 text-sm text-subtle">{empty}</p>
      ) : (
        <ul className="mt-4 space-y-3.5">
          {rows.map((row) => (
            <li key={`${row.id ?? row.name}`}>
              <div className="flex justify-between gap-3 text-sm">
                <span className="truncate font-semibold capitalize text-muted-foreground">{row.name}</span>
                <span className="shrink-0 text-subtle tabular-nums">{formatTotalDuration(row.listened_ms)}</span>
              </div>
              <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-accent">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-violet via-wisteria to-lavender"
                  style={{ width: `${Math.max(8, (row.listened_ms / max) * 100)}%` }}
                />
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function ListeningChart({ daily }: { daily: { date: string; listened_ms: number }[] }) {
  const max = Math.max(1, ...daily.map((d) => d.listened_ms));
  return (
    <section className="glass glass-inset rounded-[1.75rem] p-5">
      <h2 className="font-display text-2xl font-semibold text-heading">Listening time</h2>
      <div className="mt-5 flex h-36 items-end gap-1.5 sm:gap-2">
        {daily.map((d) => {
          const pct = d.listened_ms / max;
          const day = new Date(d.date + "T12:00:00").toLocaleDateString(undefined, { weekday: "narrow" });
          return (
            <div key={d.date} className="flex min-w-0 flex-1 flex-col items-center gap-2">
              <div className="flex h-28 w-full items-end justify-center">
                <div
                  title={formatTotalDuration(d.listened_ms)}
                  className="w-full max-w-8 rounded-full bg-gradient-to-t from-amethyst via-violet to-lavender shadow-whip transition-all"
                  style={{ height: `${Math.max(d.listened_ms > 0 ? 8 : 2, pct * 100)}%` }}
                />
              </div>
              <span className="text-[10px] font-bold uppercase tracking-wide text-subtle">{day}</span>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function MemoryCard({ item }: { item: MemoryLaneItem }) {
  const player = usePlayer();
  const playable = Boolean(item.song.playback);
  return (
    <button
      type="button"
      disabled={!playable}
      onClick={() => playable && player.play(item.song, [item.song])}
      className="glass glass-inset glow-soft group flex gap-3 rounded-[1.5rem] p-3 text-left transition-all hover:-translate-y-0.5 disabled:opacity-60"
    >
      <CoverArt src={item.song.cover_url} seed={item.song.id} title={item.song.title} className="size-16 shrink-0" />
      <div className="min-w-0">
        <Badge variant="genre" className="mb-1 capitalize">
          {item.kind.replaceAll("_", " ")}
        </Badge>
        <p className="truncate text-sm font-bold text-heading">{item.song.title}</p>
        <p className="truncate text-xs text-subtle">{artistNames(item.song.artists)}</p>
        <p className="mt-1 truncate text-xs text-muted-foreground">{item.label}</p>
      </div>
    </button>
  );
}

export function AnalyticsPage() {
  const [period, setPeriod] = useState<AnalyticsPeriod>("week");
  const [offset, setOffset] = useState(0);
  const analytics = useAnalytics(period, offset);
  const timeline = useTasteTimeline(12);
  const lane = useMemoryLane(18);
  const prefs = usePreferences();
  const updatePrefs = useUpdatePreferences();
  const wipe = useDeleteListeningHistory();

  const topQueue = useMemo(
    () => analytics.data?.top_songs.map((t) => t.song) ?? [],
    [analytics.data],
  );

  if (analytics.isError) {
    return (
      <>
        <PageHeader eyebrow="listening insights" title="Your week in purple" />
        <ErrorState error={analytics.error} onRetry={() => void analytics.refetch()} />
      </>
    );
  }

  const data = analytics.data;
  const empty = data && data.play_count === 0;

  return (
    <>
      <PageHeader
        eyebrow="listening insights"
        title={
          <>
            Your <span className="font-script text-[1.15em] font-normal text-gradient">taste</span> in numbers
          </>
        }
        description="Weekly and monthly listening, a taste timeline, and a memory lane of songs that stuck."
        actions={
          <div className="flex flex-wrap gap-2">
            {(["week", "month"] as const).map((p) => (
              <Button
                key={p}
                variant={period === p ? "cta" : "secondary"}
                size="sm"
                onClick={() => {
                  setPeriod(p);
                  setOffset(0);
                }}
              >
                {p === "week" ? "This week" : "This month"}
              </Button>
            ))}
          </div>
        }
      />

      <div className="mb-6 flex flex-wrap items-center gap-2">
        <Button
          size="sm"
          variant="secondary"
          disabled={offset >= (period === "week" ? 52 : 24)}
          onClick={() => setOffset((o) => o + 1)}
        >
          ← Earlier
        </Button>
        <Button size="sm" variant="secondary" disabled={offset === 0} onClick={() => setOffset((o) => Math.max(0, o - 1))}>
          Later →
        </Button>
        {data && (
          <p className="text-sm font-semibold text-muted-foreground">{formatRange(data.start, data.end)}</p>
        )}
      </div>

      {analytics.isPending || !data ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }, (_, i) => (
            <Skeleton key={i} className="h-28 rounded-3xl bg-accent" />
          ))}
        </div>
      ) : empty ? (
        <EmptyState
          icon={BarChart3}
          title="No listening yet in this window"
          description="Play a few tracks from Discover, For You or My Library. The player quietly records audible time when history is on."
          action={
            <Link to="/discover" className={buttonVariants({ variant: "cta" })}>
              Discover music
            </Link>
          }
        />
      ) : (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatTile label="Listening time" value={formatTotalDuration(data.total_listened_ms)} hint={`${data.play_count} plays`} />
            <StatTile label="Songs" value={String(data.unique_songs)} hint={`${data.unique_artists} artists`} />
            <StatTile
              label="Completion"
              value={data.completion_rate == null ? "—" : `${Math.round(data.completion_rate * 100)}%`}
              hint="Finished plays"
            />
            <StatTile
              label="Top genre"
              value={data.top_genres[0]?.name ?? "—"}
              hint={data.top_genres[0] ? formatTotalDuration(data.top_genres[0].listened_ms) : "Play to learn"}
            />
          </div>

          <div className="mt-6 grid gap-5 lg:grid-cols-2">
            <ListeningChart daily={data.daily} />
            <RankBars title="Top artists" rows={data.top_artists} empty="No artist plays yet." />
            <RankBars title="Top genres" rows={data.top_genres} empty="No genre tags on these plays." />
            <section className="glass glass-inset rounded-[1.75rem] p-5">
              <h2 className="font-display text-2xl font-semibold text-heading">Top songs</h2>
              <div className="mt-3 space-y-1">
                {data.top_songs.map((row) => (
                  <SongRow
                    key={row.song.id}
                    song={row.song}
                    queue={topQueue}
                    meta={`${row.play_count}× · ${formatTotalDuration(row.listened_ms)}`}
                  />
                ))}
              </div>
            </section>
          </div>
        </>
      )}

      <section className="mt-12">
        <div className="mb-4 flex items-end justify-between gap-3">
          <div>
            <p className="font-script text-2xl text-highlight">taste timeline</p>
            <h2 className="font-display text-3xl font-semibold text-heading">How your mix shifted</h2>
          </div>
        </div>
        {timeline.isPending ? (
          <Skeleton className="h-48 rounded-3xl bg-accent" />
        ) : timeline.isError ? (
          <ErrorState error={timeline.error} onRetry={() => void timeline.refetch()} />
        ) : (
          <div className="grid gap-5 lg:grid-cols-[1.4fr_1fr]">
            <div className="overflow-x-auto glass glass-inset rounded-[1.75rem] p-5">
              <div className="flex min-w-[36rem] gap-3">
                {timeline.data!.weeks.map((w) => {
                  const max = Math.max(1, ...timeline.data!.weeks.map((x) => x.listened_ms));
                  return (
                    <div key={w.week_start} className="flex w-20 flex-col items-center gap-2">
                      <div className="flex h-28 w-full items-end">
                        <div
                          className="w-full rounded-t-2xl bg-gradient-to-t from-royal-purple via-amethyst to-lilac/80"
                          style={{ height: `${Math.max(w.listened_ms > 0 ? 10 : 3, (w.listened_ms / max) * 100)}%` }}
                          title={formatTotalDuration(w.listened_ms)}
                        />
                      </div>
                      <p className="text-[10px] font-bold text-subtle">
                        {new Date(w.week_start + "T12:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" })}
                      </p>
                      <p className="line-clamp-2 text-center text-[10px] capitalize text-muted-foreground">
                        {w.top_genres[0]?.name ?? "—"}
                      </p>
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="glass glass-inset rounded-[1.75rem] p-5">
              <p className="font-script text-2xl text-cream">milestones</p>
              {timeline.data!.milestones.length === 0 ? (
                <p className="mt-3 text-sm text-lavender/80">Likes, saves and first listens will land here.</p>
              ) : (
                <ul className="mt-4 space-y-3">
                  {timeline.data!.milestones.map((m) => (
                    <li key={`${m.kind}-${m.at}`} className="flex gap-3">
                      <Sparkles className="mt-0.5 size-4 shrink-0 text-orchid-glow" />
                      <div className="min-w-0">
                        <p className="text-sm font-bold text-cream">{m.label}</p>
                        <p className="text-xs text-lavender/70">{relativeDate(m.at)}</p>
                      </div>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        )}
      </section>

      <section className="mt-12">
        <div className="mb-4">
          <p className="font-script text-2xl text-highlight">memory lane</p>
          <h2 className="font-display text-3xl font-semibold text-heading">Songs that stayed with you</h2>
        </div>
        {lane.isPending ? (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }, (_, i) => (
              <Skeleton key={i} className="h-24 rounded-3xl bg-accent" />
            ))}
          </div>
        ) : lane.isError ? (
          <ErrorState error={lane.error} onRetry={() => void lane.refetch()} />
        ) : lane.data!.items.length === 0 ? (
          <EmptyState
            icon={HeartHandshake}
            title="Memory lane is quiet"
            description="Replay a favourite after a break, or save and like a few tracks — they'll show up as flashbacks."
          />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {lane.data!.items.map((item) => (
              <MemoryCard key={`${item.kind}-${item.song.id}-${item.at}`} item={item} />
            ))}
          </div>
        )}
      </section>

      <section className="powder glass-soft glass-edge relative mt-12 overflow-hidden rounded-[2rem] p-6">
        <HairWaves className="absolute inset-0 h-full w-full opacity-50" />
        <Rose className="absolute -right-10 -top-8 size-36 opacity-80" />
        <Petal className="absolute bottom-4 left-8 size-8 rotate-12 opacity-70" />
        <div className="relative max-w-xl">
          <p className="font-script text-3xl text-cream">privacy</p>
          <h2 className="mt-1 font-display text-3xl font-semibold text-heading">Your listening, your rules</h2>
          <p className="mt-2 text-sm text-lavender">
            Tunewise only records audible time when history is on. Turning it off stops new events; delete clears
            past plays without removing likes or saves.
          </p>
          <div className="mt-5 flex flex-wrap items-center gap-3">
            <Button
              variant={prefs.data?.record_listening_history === false ? "cta" : "secondary"}
              disabled={updatePrefs.isPending || prefs.isPending}
              onClick={() =>
                updatePrefs.mutate({
                  record_listening_history: !(prefs.data?.record_listening_history ?? true),
                })
              }
            >
              <Clock3 data-icon="inline-start" />
              {prefs.data?.record_listening_history === false ? "Resume recording" : "Pause recording"}
            </Button>
            <AlertDialog>
              <AlertDialogTrigger
                className={cn(buttonVariants({ variant: "destructive", size: "default" }))}
                disabled={wipe.isPending}
              >
                <Trash2 data-icon="inline-start" />
                Delete my history
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Delete listening history?</AlertDialogTitle>
                  <AlertDialogDescription>
                    This permanently removes your listening events and playback sessions. Likes, saves and My Library
                    stay. Recommendations will lean more on explicit feedback until you listen again.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Keep history</AlertDialogCancel>
                  <AlertDialogAction
                    onClick={() => wipe.mutate()}
                    className="bg-rose text-white hover:bg-rose/90"
                  >
                    Delete history
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          </div>
          <p className="mt-3 flex items-center gap-2 text-xs text-lavender/80">
            <Disc3 className="size-3.5" />
            History recording is {prefs.data?.record_listening_history === false ? "off" : "on"}
            {prefs.data ? ` · timezone ${prefs.data.timezone}` : ""}
          </p>
          <p className="mt-2 flex items-center gap-2 text-xs text-lavender/80">
            <Mic2 className="size-3.5" />
            Open <Link to="/companion" className="font-bold text-cream underline-offset-2 hover:underline">Companion</Link> for
            today's mood mix.
          </p>
        </div>
      </section>
    </>
  );
}
