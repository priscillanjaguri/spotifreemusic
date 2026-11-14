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
import {
  ButterflyDrift,
  FairyLights,
  MOOD,
  MoodAccent,
  Petal,
  PhotoCollage,
  PhotoHero,
  PhotoStatShell,
} from "@/components/decor";
import { Logo } from "@/components/layout/logo";
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

function StatCard({
  icon: Icon,
  label,
  value,
  hint,
  photo,
  position,
  to,
}: {
  icon: LucideIcon;
  label: string;
  value: string | number | undefined;
  hint?: string;
  photo: string;
  position?: string;
  to: string;
}) {
  return (
    <Link to={to} className="glow-soft group block transition-transform duration-200 hover:-translate-y-0.5">
      <PhotoStatShell src={photo} position={position}>
        <div className="gloss grid size-11 place-items-center rounded-2xl bg-gradient-to-br from-orchid-glow/90 to-heliotrope text-cream ring-1 ring-white/35 shadow-polish">
          <Icon className="size-5" />
        </div>
        <p className="mt-4 text-sm font-bold uppercase tracking-wide text-orchid-glow">{label}</p>
        {value === undefined ? (
          <Skeleton className="mt-1 h-9 w-16 bg-white/20" />
        ) : (
          <p className="font-display text-4xl font-semibold text-cream drop-shadow-[0_2px_12px_rgb(0_0_0_/_0.45)] [font-variant-numeric:lining-nums]">
            {typeof value === "number" ? value.toLocaleString() : value}
          </p>
        )}
        {hint && <p className="mt-1 text-xs font-bold text-pink-glow">{hint}</p>}
      </PhotoStatShell>
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
      <MoodAccent src={MOOD.collageFull} side="right" className="opacity-65" />
      <ButterflyDrift className="opacity-40" />
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
    <section className="relative overflow-hidden rounded-[1.75rem] p-5 ring-1 ring-lavender/25 md:col-span-2">
      <MoodAccent src={MOOD.beachFull} side="right" className="opacity-50" />
      <div
        aria-hidden
        className="absolute inset-0 bg-gradient-to-r from-[#24112e]/92 via-[#31183f]/85 to-[#24112e]/55"
      />
      <div className="relative mb-4 flex items-end justify-between gap-3">
        <div>
          <p className="font-script text-2xl text-orchid-glow">this week</p>
          <h2 className="font-display text-2xl font-semibold text-cream">Listening overview</h2>
        </div>
        <Link to="/analytics" className="text-sm font-bold text-pink-glow hover:text-cream">
          Full analytics →
        </Link>
      </div>
      <div className="relative flex h-36 items-end gap-2">
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
              <span className="text-[10px] font-bold uppercase tracking-wide text-lavender/80">{day}</span>
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
        <PhotoHero src={MOOD.lookingUp} position="center 22%" dense>
          <Logo className="mb-3" />
          <p className="font-script text-2xl text-orchid-glow">{today}</p>
          <h1 className="font-display text-4xl font-semibold text-cream">{greeting()}, {firstName}</h1>
        </PhotoHero>
        <div className="mt-6">
          <ErrorState
            error={recent.error ?? facets.error}
            onRetry={() => {
              void recent.refetch();
              void facets.refetch();
            }}
          />
        </div>
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
      <PhotoHero src={MOOD.lookingUp} position="center 20%" className="min-h-[20rem] sm:min-h-[24rem]">
        <FairyLights warm className="opacity-80" />
        <MoodAccent src={MOOD.lantern} side="right" className="opacity-50" />
        <Logo className="mb-4 drop-shadow-lg" />
        <p className="font-script text-2xl leading-none text-orchid-glow sm:text-[1.7rem]">{today}</p>
        <h1 className="mt-2 font-display text-4xl font-semibold tracking-tight text-cream sm:text-5xl">
          {greeting()}, <span className="font-script text-[1.15em] font-normal text-gradient">{firstName}</span>
        </h1>
        <p className="mt-2 max-w-xl text-sm text-lavender/95 sm:text-base">
          {total === undefined
            ? "Gathering your music…"
            : isNew
              ? "Your collection is empty for now. Let's find the first songs worth keeping."
              : `You've saved ${plural(total, "song")} so far — headphones on, looking up.`}
        </p>
        <Link to="/discover" className={cn(buttonVariants({ variant: "cta", size: "lg" }), "mt-5 w-fit")}>
          <Compass data-icon="inline-start" /> Discover music
        </Link>
      </PhotoHero>

      <section className="relative mt-8 overflow-hidden rounded-[2rem] p-4 ring-1 ring-orchid-glow/25 sm:p-6">
        <PhotoCollage opacity={0.72} drift />
        <div
          aria-hidden
          className="absolute inset-0 bg-gradient-to-b from-[#5a1a78]/35 via-[#2a1040]/62 to-[#12061c]/88"
        />
        <ButterflyDrift className="opacity-40" />

        <div className="relative mb-4">
          <p className="font-script text-2xl text-orchid-glow">your week in colour</p>
          <h2 className="font-display text-2xl font-semibold text-cream sm:text-3xl">Listening pulse</h2>
        </div>

        <div className="relative grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
          <StatCard
            icon={Clock3}
            label="Listening time"
            value={week.data ? formatTotalDuration(week.data.total_listened_ms) : undefined}
            hint={listenHint}
            photo={MOOD.rosesFull}
            position="center 40%"
            to="/analytics"
          />
          <StatCard
            icon={Library}
            label="Songs saved"
            value={total}
            photo={MOOD.collageFull}
            position="center 15%"
            to="/collection"
          />
          <StatCard
            icon={Tags}
            label="Top genre"
            value={week.data?.top_genres[0]?.name ?? facets.data?.genres[0]?.name}
            hint="This week"
            photo={MOOD.beachFull}
            position="center 45%"
            to="/analytics"
          />
          <StatCard
            icon={Mic2}
            label="Artists"
            value={facets.data?.artists.length}
            photo={MOOD.lantern}
            position="center 40%"
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
      </section>

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
          className="glow-soft group relative overflow-hidden rounded-[1.75rem] p-5 ring-1 ring-lavender/25"
        >
          <MoodAccent src={MOOD.rosesFull} side="right" className="opacity-70" />
          <div aria-hidden className="absolute inset-0 bg-gradient-to-r from-[#1a0b28]/88 to-[#1a0b28]/35" />
          <Sparkles className="absolute right-4 top-4 z-10 size-8 text-orchid-glow opacity-70" />
          <p className="relative font-script text-3xl text-cream">daily companion</p>
          <p className="relative mt-1 text-sm text-lavender">A mood-aware mix from your taste and recent listens.</p>
          <span className="relative mt-3 inline-flex items-center gap-1 text-sm font-bold text-cream group-hover:text-highlight">
            Open companion <ArrowRight className="size-4" />
          </span>
        </Link>
        <Link
          to="/analytics"
          className="glow-soft group relative overflow-hidden rounded-[1.75rem] p-5 ring-1 ring-lavender/25"
        >
          <MoodAccent src={MOOD.beachFull} side="right" className="opacity-65" />
          <div aria-hidden className="absolute inset-0 bg-gradient-to-r from-[#1a0b28]/88 to-[#1a0b28]/35" />
          <BarChart3 className="absolute right-4 top-4 size-8 text-lilac opacity-70" />
          <p className="relative font-script text-3xl text-orchid-glow">listening insights</p>
          <p className="relative mt-1 text-sm text-lavender/90">Weekly charts, taste timeline and memory lane.</p>
          <span className="relative mt-3 inline-flex items-center gap-1 text-sm font-bold text-pink-glow group-hover:text-cream">
            Open analytics <ArrowRight className="size-4" />
          </span>
        </Link>
        <section className="relative overflow-hidden rounded-[1.75rem] p-5 ring-1 ring-lavender/25 md:col-span-2 xl:col-span-1">
          <MoodAccent src={MOOD.collageFull} side="right" className="opacity-60" />
          <div aria-hidden className="absolute inset-0 bg-gradient-to-r from-[#1a0b28]/9 to-[#1a0b28]/4" />
          <Petal className="absolute top-4 right-6 size-8 rotate-45 opacity-70" />
          <Disc3 className="relative mb-2 size-5 text-orchid-glow" />
          <p className="relative font-script text-3xl text-orchid-glow">how For You listens</p>
          <p className="relative mt-1 text-sm text-lavender/90">
            Likes, saves, completes and replays shape your mix. Skips stay neutral.
          </p>
          <Link
            to="/recommendations"
            className="relative mt-3 inline-flex items-center gap-1 text-sm font-bold text-pink-glow hover:text-cream"
          >
            See your picks <ArrowRight className="size-4" />
          </Link>
        </section>
      </div>
    </>
  );
}
