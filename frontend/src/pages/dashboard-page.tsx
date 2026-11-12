import { ArrowRight, Compass, Disc3, Library, Mic2, Sparkles, Tags, type LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";
import { PageHeader } from "@/components/layout/app-shell";
import { SongRow } from "@/components/music/song-row";
import { EmptyState, ErrorState, SongListSkeleton } from "@/components/states";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/lib/auth";
import { useFacets, useRecentlyAdded, useRemoveFromCollection } from "@/lib/collection";
import { greeting, plural, relativeDate } from "@/lib/format";
import type { Facet } from "@/lib/types";
import { cn } from "@/lib/utils";

export const QUICK_SEARCHES = ["lofi", "ambient", "jazz", "synthwave", "piano", "indie rock", "folk"];

const STAT_TONES = {
  amethyst: "from-amethyst/35 to-amethyst/5 ring-amethyst/30 text-violet-glow",
  orchid: "from-orchid/35 to-plum/5 ring-orchid/30 text-magenta",
  wisteria: "from-wisteria/35 to-iris/5 ring-wisteria/30 text-lavender",
  lavender: "from-lavender/25 to-eggplant/5 ring-lavender/25 text-lilac",
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
      className="group rounded-2xl border bg-card/80 p-4 transition-all hover:-translate-y-0.5 hover:border-iris/60 hover:shadow-glow sm:p-5"
    >
      <div className={cn("grid size-10 place-items-center rounded-xl bg-gradient-to-br ring-1", STAT_TONES[tone])}>
        <Icon className="size-5" />
      </div>
      <p className="mt-4 text-sm text-muted-foreground">{label}</p>
      {value === undefined ? (
        <Skeleton className="mt-1 h-8 w-14 bg-eggplant" />
      ) : (
        <p className="mt-0.5 text-3xl font-semibold tracking-tight text-lilac tabular-nums">{value.toLocaleString()}</p>
      )}
    </Link>
  );
}

function FacetBars({ title, facets, param, empty }: { title: string; facets: Facet[]; param: string; empty: string }) {
  const top = facets.slice().sort((a, b) => b.count - a.count).slice(0, 5);
  const max = top[0]?.count ?? 1;
  return (
    <section className="rounded-2xl border bg-card/80 p-5">
      <h2 className="font-semibold text-lilac">{title}</h2>
      {top.length === 0 ? (
        <p className="mt-3 text-sm text-dusk">{empty}</p>
      ) : (
        <ul className="mt-4 space-y-3">
          {top.map((f) => (
            <li key={f.id}>
              <Link
                to={`/collection?${param}=${param === "genre" ? encodeURIComponent(f.name) : f.id}`}
                className="group block"
              >
                <div className="flex justify-between text-sm">
                  <span className="truncate text-mauve capitalize group-hover:text-lavender">{f.name}</span>
                  <span className="text-dusk tabular-nums">{f.count}</span>
                </div>
                <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-eggplant">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-amethyst via-orchid to-magenta"
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
    <section className="relative overflow-hidden rounded-2xl border border-orchid/30 bg-gradient-to-br from-plum/40 via-grape to-grape p-6">
      <div aria-hidden className="absolute -top-16 -right-10 size-48 rounded-full bg-orchid/30 blur-3xl" />
      <div className="relative">
        <Compass className="size-6 text-magenta" />
        <h2 className="mt-3 text-lg font-semibold text-lilac">Find something new</h2>
        <p className="mt-1 text-sm text-mauve">Jump into a mood. Every result can be played and saved in one tap.</p>
        <div className="mt-4 flex flex-wrap gap-2">
          {QUICK_SEARCHES.slice(0, 5).map((q) => (
            <Link
              key={q}
              to={`/discover?q=${encodeURIComponent(q)}`}
              className="rounded-full border border-orchid/30 bg-night/40 px-3 py-1 text-sm text-lilac transition-colors hover:border-magenta hover:text-magenta"
            >
              {q}
            </Link>
          ))}
        </div>
      </div>
    </section>
  );
}

export function DashboardPage() {
  const { user } = useAuth();
  const recent = useRecentlyAdded(6);
  const facets = useFacets();
  const remove = useRemoveFromCollection();

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
            {greeting()}, <span className="text-gradient">{firstName}</span>
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
        <StatCard icon={Library} label="Songs saved" value={total} tone="amethyst" to="/collection" />
        <StatCard icon={Mic2} label="Artists" value={facets.data?.artists.length} tone="orchid" to="/collection" />
        <StatCard icon={Disc3} label="Albums" value={facets.data?.albums.length} tone="wisteria" to="/collection" />
        <StatCard icon={Tags} label="Genres" value={facets.data?.genres.length} tone="lavender" to="/collection" />
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-[minmax(0,1.7fr)_minmax(0,1fr)]">
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-lg font-semibold text-lilac">Recently added</h2>
            {!isNew && (
              <Link to="/collection" className="inline-flex items-center gap-1 text-sm text-lavender hover:text-magenta">
                See all <ArrowRight className="size-4" />
              </Link>
            )}
          </div>
          {recent.isPending ? (
            <SongListSkeleton rows={5} />
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
            <div className="divide-y divide-border/60 overflow-hidden rounded-2xl border bg-card/80">
              {recent.data!.items.map((item) => (
                <SongRow
                  key={item.song.id}
                  song={item.song}
                  queue={songs}
                  meta={relativeDate(item.added_at)}
                  action={{
                    kind: "remove",
                    pending: remove.isPending && remove.variables?.id === item.song.id,
                    onRemove: () => remove.mutate(item.song),
                  }}
                />
              ))}
            </div>
          )}
        </section>

        <div className="space-y-6">
          <DiscoverCallout />
          {facets.data && !isNew && (
            <FacetBars title="Your top genres" facets={facets.data.genres} param="genre" empty="No genre tags yet." />
          )}
          {facets.data && !isNew && (
            <FacetBars title="Most-saved artists" facets={facets.data.artists} param="artist" empty="No artists yet." />
          )}
          <section className="rounded-2xl border border-dashed border-iris/40 bg-aubergine/60 p-5">
            <div className="flex items-center gap-2 text-sm font-semibold text-lavender">
              <Sparkles className="size-4 text-magenta" /> Recommendations are tuning up
            </div>
            <p className="mt-2 text-sm text-mauve">
              Soon Tunewise will suggest songs based on what your saved music has in common. The more you collect, the
              sharper those picks will be.
            </p>
            <Link to="/discover" className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-lavender hover:text-magenta">
              Keep collecting <ArrowRight className="size-4" />
            </Link>
          </section>
        </div>
      </div>
    </>
  );
}
