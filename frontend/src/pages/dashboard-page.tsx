import { ArrowRight, Compass, Disc3, Library, Mic2, Tags, type LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";
import { HairWaves, Petal, Rose } from "@/components/decor";
import { PageHeader } from "@/components/layout/app-shell";
import { SongCard } from "@/components/music/song-card";
import { EmptyState, ErrorState } from "@/components/states";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/lib/auth";
import { useFacets, useRecentlyAdded } from "@/lib/collection";
import { greeting, plural, relativeDate } from "@/lib/format";
import type { Facet } from "@/lib/types";
import { cn } from "@/lib/utils";

export const QUICK_SEARCHES = ["lofi", "ambient", "jazz", "synthwave", "piano", "indie rock", "folk"];

// Each stat gets its own shade from the palette, lightest to deepest.
const STAT_TONES = {
  lavender: "from-violet-sheen to-violet-shadow",
  wisteria: "from-mauve/80 to-amethyst",
  heliotrope: "from-amethyst-sheen to-amethyst-shadow",
  royal: "from-royal-purple-sheen to-royal-purple-shadow",
};

function StatCard({
  icon: Icon,
  label,
  value,
  tone,
  to,
}: {
  icon: LucideIcon;
  label: string;
  value: number | undefined;
  tone: keyof typeof STAT_TONES;
  to: string;
}) {
  return (
    <Link
      to={to}
      className="group rounded-3xl border border-border bg-card satin p-4 shadow-whip transition-all hover:-translate-y-0.5 hover:bg-surface-raised hover:shadow-whip-lg sm:p-5"
    >
      <div className={cn("gloss grid size-11 place-items-center rounded-full bg-gradient-to-br text-cream ring-1 ring-lavender/20 shadow-polish", STAT_TONES[tone])}>
        <Icon className="size-5" />
      </div>
      <p className="mt-4 text-sm font-semibold text-muted-foreground">{label}</p>
      {value === undefined ? (
        <Skeleton className="mt-1 h-9 w-14 bg-accent" />
      ) : (
        <p className="font-display text-4xl font-semibold text-heading [font-variant-numeric:lining-nums]">{value.toLocaleString()}</p>
      )}
    </Link>
  );
}

function FacetBars({ title, facets, param, empty }: { title: string; facets: Facet[]; param: string; empty: string }) {
  const top = facets.slice().sort((a, b) => b.count - a.count).slice(0, 5);
  const max = top[0]?.count ?? 1;
  return (
    <section className="rounded-3xl border border-border bg-card satin p-5 shadow-whip">
      <h2 className="font-display text-2xl font-semibold text-heading">{title}</h2>
      {top.length === 0 ? (
        <p className="mt-3 text-sm text-subtle">{empty}</p>
      ) : (
        <ul className="mt-4 space-y-3.5">
          {top.map((f) => (
            <li key={f.id}>
              <Link to={`/collection?${param}=${param === "genre" ? encodeURIComponent(f.name) : f.id}`} className="group block">
                <div className="flex justify-between text-sm">
                  <span className="truncate font-semibold text-muted-foreground capitalize group-hover:text-accent-foreground">{f.name}</span>
                  <span className="text-subtle tabular-nums">{f.count}</span>
                </div>
                <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-accent">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-violet via-wisteria to-lavender"
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
    <section className="powder relative overflow-hidden rounded-3xl border border-lavender/15 bg-satin-violet p-6 shadow-whip-lg">
      <HairWaves className="absolute inset-0 h-full w-full opacity-60" />
      <Rose className="absolute -top-8 -right-8 size-32 opacity-90 drop-shadow-lg" />
      <div className="relative">
        <p className="font-script text-3xl text-cream">find something new</p>
        <p className="mt-1 max-w-[16rem] text-sm text-lavender">Jump into a mood. Every result can be played and saved in one tap.</p>
        <div className="mt-4 flex flex-wrap gap-2">
          {QUICK_SEARCHES.slice(0, 5).map((q) => (
            <Link
              key={q}
              to={`/discover?q=${encodeURIComponent(q)}`}
              className="rounded-full bg-deep-purple/60 px-3.5 py-1.5 text-sm font-bold text-cream ring-1 ring-lavender/20 transition-colors hover:bg-deep-purple"
            >
              {q}
            </Link>
          ))}
        </div>
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
              : `You've saved ${plural(total, "song")} so far. Here's what your collection looks like today.`
        }
        actions={
          <Link to="/discover" className={buttonVariants({ variant: "cta", size: "lg" })}>
            <Compass data-icon="inline-start" /> Discover music
          </Link>
        }
      />

      <div className="grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4">
        <StatCard icon={Library} label="Songs saved" value={total} tone="lavender" to="/collection" />
        <StatCard icon={Mic2} label="Artists" value={facets.data?.artists.length} tone="wisteria" to="/collection" />
        <StatCard icon={Disc3} label="Albums" value={facets.data?.albums.length} tone="heliotrope" to="/collection" />
        <StatCard icon={Tags} label="Genres" value={facets.data?.genres.length} tone="royal" to="/collection" />
      </div>

      <section className="mt-10">
        <SectionTitle
          action={
            !isNew && (
              <Link to="/collection" className="inline-flex items-center gap-1 text-sm font-bold text-accent-foreground hover:text-highlight">
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
          <FacetBars title="Your top genres" facets={facets.data.genres} param="genre" empty="No genre tags yet." />
        )}
        {facets.data && !isNew && (
          <FacetBars title="Most-saved artists" facets={facets.data.artists} param="artist" empty="No artists yet." />
        )}
        <section className="relative overflow-hidden rounded-3xl border border-dashed border-lilac/40 bg-satin-deep p-5 md:col-span-2 xl:col-span-3">
          <Petal className="absolute top-4 right-6 size-8 rotate-45 opacity-70" />
          <p className="font-script text-3xl text-highlight">recommendations are tuning up</p>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Soon Tunewise will suggest songs based on what your saved music has in common. The more you collect, the
            sharper those picks will be.
          </p>
          <Link to="/discover" className="mt-3 inline-flex items-center gap-1 text-sm font-bold text-accent-foreground hover:text-highlight">
            Keep collecting <ArrowRight className="size-4" />
          </Link>
        </section>
      </div>
    </>
  );
}
