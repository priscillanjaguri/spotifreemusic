import {
  ArrowRight,
  BarChart3,
  Clock3,
  Compass,
  Disc3,
  Heart,
  Library,
  Mic2,
  Sparkles,
  Tags,
  type LucideIcon,
} from "lucide-react";
import { Link } from "react-router-dom";
import { HairWaves, Petal, Rose } from "@/components/decor";
import { PageHeader } from "@/components/layout/app-shell";
import { RecommendationCard } from "@/components/music/recommendation-card";
import { SongCard } from "@/components/music/song-card";
import { EmptyState, ErrorState } from "@/components/states";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useAnalytics } from "@/lib/analytics";
import { useAuth } from "@/lib/auth";
import { useFacets, useRecentlyAdded } from "@/lib/collection";
import { formatTotalDuration, greeting, plural, relativeDate } from "@/lib/format";
import { useForYou } from "@/lib/recommendations";
import type { Facet } from "@/lib/types";
import { cn } from "@/lib/utils";

export const QUICK_SEARCHES = ["lofi", "ambient", "jazz", "synthwave", "piano", "indie rock", "folk"];

const STAT_TONES = {
  lavender: "from-violet-sheen to-violet-shadow",
  wisteria: "from-mauve/80 to-amethyst",
  heliotrope: "from-amethyst-sheen to-amethyst-shadow",
  royal: "from-royal-purple-sheen to-royal-purple-shadow",
  pink: "from-orchid-glow/80 to-heliotrope",
};

function StatCard({
  icon: Icon,
  label,
  value,
  hint,
  tone,
  to,
}: {
  icon: LucideIcon;
  label: string;
  value: string | number | undefined;
  hint?: string;
  tone: keyof typeof STAT_TONES;
  to: string;
}) {
  return (
    <Link
      to={to}
      className="glass glass-inset glow-soft group rounded-[1.6rem] p-4 sm:p-5"
    >
      <div
        className={cn(
          "gloss grid size-11 place-items-center rounded-2xl bg-gradient-to-br text-cream ring-1 ring-white/20 shadow-polish",
          STAT_TONES[tone],
        )}
      >
        <Icon className="size-5" />
      </div>
      <p className="mt-4 text-sm font-semibold text-muted-foreground">{label}</p>
      {value === undefined ? (
        <Skeleton className="mt-1 h-9 w-16 bg-accent" />
      ) : (
        <p className="font-display text-4xl font-semibold text-heading [font-variant-numeric:lining-nums]">
          {typeof value === "number" ? value.toLocaleString() : value}
        </p>
      )}
      {hint && <p className="mt-1 text-xs font-semibold text-orchid-glow/90">{hint}</p>}
    </Link>
  );
}

function FacetBars({ title, facets, param, empty }: { title: string; facets: Facet[]; param: string; empty: string }) {
  const top = facets.slice().sort((a, b) => b.count - a.count).slice(0, 5);
  const max = top[0]?.count ?? 1;
  return (
    <section className="glass glass-inset rounded-[1.75rem] p-5">
      <h2 className="font-display text-2xl font-semibold text-heading">{title}</h2>
      {top.length === 0 ? (
        <p className="mt-3 text-sm text-subtle">{empty}</p>
      ) : (
        <ul className="mt-4 space-y-3.5">
          {top.map((f) => (
            <li key={f.id}>
              <Link
                to={`/collection?${param}=${param === "genre" ? encodeURIComponent(f.name) : f.id}`}
                className="group block"
              >
                <div className="flex justify-between text-sm">
                  <span className="truncate font-semibold capitalize text-muted-foreground group-hover:text-accent-foreground">
                    {f.name}
                  </span>
                  <span className="text-subtle tabular-nums">{f.count}</span>
                </div>
                <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-white/10">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-heliotrope via-wisteria to-pink-glow"
                    style={{ width: `${Math.max(8, (f.count / max) * 100)}%` }}
                  />
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function DiscoverCallout() {
  return (
    <section className="powder glass-soft glass-edge relative overflow-hidden rounded-[1.75rem] p-6">
      <HairWaves className="absolute inset-0 h-full w-full opacity-50" />
      <Rose className="absolute -top-8 -right-8 size-32 opacity-80 drop-shadow-lg" />
      <div className="relative">
        <p className="font-script text-3xl text-cream">find something new</p>
        <p className="mt-1 max-w-[16rem] text-sm text-lavender">
          Jump into a mood. Every result can be played and saved in one tap.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          {QUICK_SEARCHES.slice(0, 5).map((q) => (
            <Link
              key={q}
              to={`/discover?q=${encodeURIComponent(q)}`}
              className="rounded-full bg-deep-purple/50 px-3.5 py-1.5 text-sm font-bold text-cream ring-1 ring-white/15 transition-colors hover:bg-deep-purple/80"
            >
              {q}
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}

function ListeningSpark({ daily }: { daily: { date: string; listened_ms: number }[] }) {
  const max = Math.max(1, ...daily.map((d) => d.listened_ms));
  return (
    <section className="glass glass-inset rounded-[1.75rem] p-5 md:col-span-2">
      <div className="mb-4 flex items-end justify-between gap-3">
        <div>
          <p className="font-script text-2xl text-highlight">this week</p>
          <h2 className="font-display text-2xl font-semibold text-heading">Listening overview</h2>
        </div>
        <Link to="/analytics" className="text-sm font-bold text-accent-foreground hover:text-highlight">
          Full analytics →
        </Link>
      </div>
      <div className="flex h-36 items-end gap-2">
        {daily.map((d) => {
          const pct = d.listened_ms / max;
          const day = new Date(d.date + "T12:00:00").toLocaleDateString(undefined, { weekday: "narrow" });
          return (
            <div key={d.date} className="flex min-w-0 flex-1 flex-col items-center gap-2">
              <div className="flex h-28 w-full items-end justify-center">
                <div
                  title={formatTotalDuration(d.listened_ms)}
                  className="w-full max-w-9 rounded-t-2xl bg-gradient-to-t from-amethyst via-heliotrope to-pink-glow/90 shadow-glow"
                  style={{ height: `${Math.max(d.listened_ms > 0 ? 10 : 3, pct * 100)}%` }}
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

function SectionTitle({ children, action }: { children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="mb-4 flex items-end justify-between">
      <h2 className="font-display text-3xl font-semibold text-heading">{children}</h2>
      {action}
    </div>
  );
}

export function DashboardPage() {
  const { user } = useAuth();
  const recent = useRecentlyAdded(6);
  const facets = useFacets();
  const forYou = useForYou(6);
  const week = useAnalytics("week", 0);

  const firstName = user?.display_name.split(" ")[0] ?? "";
  const total = recent.data?.total;
  const today = new Date().toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" });

  if (recent.isError || facets.isError) {
    return (
      <>
        <PageHeader eyebrow={today} title={`${greeting()}, ${firstName}`} />
        <ErrorState
          error={recent.error ?? facets.error}
          onRetry={() => {
            void recent.refetch();
            void facets.refetch();
          }}
        />
      </>
    );
  }

  const isNew = total === 0;
  const songs = recent.data?.items.map((i) => i.song) ?? [];
  const forYouQueue = forYou.data?.items.map((i) => i.song) ?? [];
  const listenHint =
    week.data && week.data.play_count > 0
      ? `${week.data.play_count} plays`
      : "Play to start tracking";

  return (
    <>
      <PageHeader
        eyebrow={today}
        title={
          <>
            {greeting()}, <span className="font-script text-[1.2em] font-normal text-gradient">{firstName}</span>
          </>
        }
        description={
          total === undefined
            ? "Gathering your music…"
            : isNew
              ? "Your collection is empty for now. Let's find the first songs worth keeping."
              : `You've saved ${plural(total, "song")} so far. Here's your glassy dashboard.`
        }
        actions={
          <Link to="/discover" className={buttonVariants({ variant: "cta", size: "lg" })}>
            <Compass data-icon="inline-start" /> Discover music
          </Link>
        }
      />

      <div className="glass-strong glass-inset relative overflow-hidden rounded-[2rem] p-4 sm:p-6">
        <div className="pointer-events-none absolute -right-16 -top-16 size-56 rounded-full bg-pink-glow/20 blur-3xl animate-glow-pulse" />
        <div className="pointer-events-none absolute -left-10 bottom-0 size-48 rounded-full bg-heliotrope/20 blur-3xl" />

        <div className="relative grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
          <StatCard
            icon={Clock3}
            label="Listening time"
            value={week.data ? formatTotalDuration(week.data.total_listened_ms) : undefined}
            hint={listenHint}
            tone="pink"
            to="/analytics"
          />
          <StatCard icon={Library} label="Songs saved" value={total} tone="lavender" to="/collection" />
          <StatCard
            icon={Tags}
            label="Top genre"
            value={week.data?.top_genres[0]?.name ?? facets.data?.genres[0]?.name}
            hint="This week"
            tone="wisteria"
            to="/analytics"
          />
          <StatCard
            icon={Mic2}
            label="Artists"
            value={facets.data?.artists.length}
            tone="heliotrope"
            to="/collection"
          />
        </div>

        <div className="relative mt-5 grid gap-5 md:grid-cols-3">
          {week.data ? (
            <ListeningSpark daily={week.data.daily} />
          ) : (
            <section className="glass rounded-[1.75rem] p-5 md:col-span-2">
              <Skeleton className="h-36 w-full rounded-2xl bg-accent" />
            </section>
          )}
          <FacetBars
            title="Genre mix"
            facets={facets.data?.genres ?? []}
            param="genre"
            empty="Save songs to see genre bars."
          />
        </div>
      </div>

      <section className="mt-10">
        <SectionTitle
          action={
            <Link
              to="/recommendations"
              className="inline-flex items-center gap-1 text-sm font-bold text-accent-foreground hover:text-highlight"
            >
              Open For You <ArrowRight className="size-4" />
            </Link>
          }
        >
          For You
        </SectionTitle>
        {forYou.isPending ? (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4 xl:grid-cols-6">
            {Array.from({ length: 6 }, (_, i) => (
              <Skeleton key={i} className="aspect-[3/4] rounded-3xl bg-accent" />
            ))}
          </div>
        ) : forYou.isError ? (
          <ErrorState error={forYou.error} onRetry={() => void forYou.refetch()} />
        ) : forYouQueue.length === 0 ? (
          <EmptyState
            icon={Heart}
            title="Recommendations are warming up"
            description="Save a few songs or pick seed genres on For You — then Spotifree can start matching your taste."
            action={
              <Link to="/recommendations" className={buttonVariants({ variant: "cta" })}>
                Set your taste
              </Link>
            }
          />
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4 xl:grid-cols-6">
            {forYou.data!.items.map((item) => (
              <RecommendationCard key={item.song.id} item={item} queue={forYouQueue} context="dashboard" />
            ))}
          </div>
        )}
      </section>

      <section className="mt-10">
        <SectionTitle
          action={
            !isNew && (
              <Link
                to="/collection"
                className="inline-flex items-center gap-1 text-sm font-bold text-accent-foreground hover:text-highlight"
              >
                See all <ArrowRight className="size-4" />
              </Link>
            )
          }
        >
          Recently added
        </SectionTitle>
        {recent.isPending ? (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4 xl:grid-cols-6">
            {Array.from({ length: 6 }, (_, i) => (
              <Skeleton key={i} className="aspect-[3/4] rounded-3xl bg-accent" />
            ))}
          </div>
        ) : isNew ? (
          <EmptyState
            icon={Library}
            title="Nothing saved yet"
            description="Search for an artist, a genre or a feeling, then tap + to keep a song. It will show up here."
            action={
              <Link to="/discover" className={buttonVariants({ variant: "cta" })}>
                <Compass data-icon="inline-start" /> Start discovering
              </Link>
            }
          />
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4 xl:grid-cols-6">
            {recent.data!.items.map((item) => (
              <SongCard key={item.song.id} song={item.song} queue={songs} meta={relativeDate(item.added_at)} />
            ))}
          </div>
        )}
      </section>

      <div className="mt-10 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        <DiscoverCallout />
        {facets.data && !isNew && (
          <FacetBars title="Most-saved artists" facets={facets.data.artists} param="artist" empty="No artists yet." />
        )}
        <Link
          to="/companion"
          className="glass-soft glass-edge glow-soft group relative overflow-hidden rounded-[1.75rem] p-5"
        >
          <Sparkles className="absolute right-4 top-4 size-8 text-orchid-glow opacity-70" />
          <p className="font-script text-3xl text-cream">daily companion</p>
          <p className="mt-1 text-sm text-lavender">A mood-aware mix from your taste and recent listens.</p>
          <span className="mt-3 inline-flex items-center gap-1 text-sm font-bold text-cream group-hover:text-highlight">
            Open companion <ArrowRight className="size-4" />
          </span>
        </Link>
        <Link
          to="/analytics"
          className="glass glow-soft group relative overflow-hidden rounded-[1.75rem] p-5"
        >
          <BarChart3 className="absolute right-4 top-4 size-8 text-lilac opacity-70" />
          <p className="font-script text-3xl text-highlight">listening insights</p>
          <p className="mt-1 text-sm text-muted-foreground">Weekly charts, taste timeline and memory lane.</p>
          <span className="mt-3 inline-flex items-center gap-1 text-sm font-bold text-accent-foreground group-hover:text-highlight">
            Open analytics <ArrowRight className="size-4" />
          </span>
        </Link>
        <section className="glass-soft relative overflow-hidden rounded-[1.75rem] p-5 md:col-span-2 xl:col-span-1">
          <Petal className="absolute top-4 right-6 size-8 rotate-45 opacity-70" />
          <Disc3 className="mb-2 size-5 text-orchid-glow" />
          <p className="font-script text-3xl text-highlight">how For You listens</p>
          <p className="mt-1 text-sm text-muted-foreground">
            Likes, saves, completes and replays shape your mix. Skips stay neutral.
          </p>
          <Link
            to="/recommendations"
            className="mt-3 inline-flex items-center gap-1 text-sm font-bold text-accent-foreground hover:text-highlight"
          >
            See your picks <ArrowRight className="size-4" />
          </Link>
        </section>
      </div>
    </>
  );
}
