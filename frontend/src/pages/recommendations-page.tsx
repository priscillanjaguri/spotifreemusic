import { HeartHandshake, Sparkles } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { HairWaves, Petal, Rose } from "@/components/decor";
import { PageHeader } from "@/components/layout/app-shell";
import { RecommendationCard } from "@/components/music/recommendation-card";
import { EmptyState, ErrorState } from "@/components/states";
import { buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useForYou, useSeedGenres, useSimilar } from "@/lib/recommendations";
import { cn } from "@/lib/utils";

const SEED_GENRES = [
  "lofi",
  "ambient",
  "jazz",
  "synthwave",
  "indie",
  "folk",
  "pop",
  "electronic",
  "piano",
  "hiphop",
  "house",
  "rock",
];

function GridSkeleton() {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4 xl:grid-cols-4">
      {Array.from({ length: 8 }, (_, i) => (
        <Skeleton key={i} className="aspect-[3/4] rounded-3xl bg-accent" />
      ))}
    </div>
  );
}

export function RecommendationsPage() {
  const [params, setParams] = useSearchParams();
  const similarId = Number(params.get("similar") || 0) || null;
  const forYou = useForYou(24);
  const similar = useSimilar(similarId, 12);
  const seed = useSeedGenres();
  const [picked, setPicked] = useState<string[]>([]);

  const active = similarId ? similar : forYou;
  const items = active.data?.items ?? [];
  const queue = useMemo(() => items.map((i) => i.song), [items]);

  const clearSimilar = () => {
    const next = new URLSearchParams(params);
    next.delete("similar");
    setParams(next, { replace: true });
  };

  const toggleGenre = (g: string) => {
    setPicked((prev) => {
      const next = prev.includes(g) ? prev.filter((x) => x !== g) : [...prev, g].slice(0, 12);
      seed.mutate(next);
      return next;
    });
  };

  if (active.isError) {
    return (
      <>
        <PageHeader eyebrow="for you" title="Picks with your name on them" />
        <ErrorState error={active.error} onRetry={() => void active.refetch()} />
      </>
    );
  }

  return (
    <>
      <PageHeader
        eyebrow="for you"
        title={
          similarId ? (
            <>
              More like <span className="font-script text-[1.15em] font-normal text-gradient">this</span>
            </>
          ) : (
            <>
              Picks with your <span className="font-script text-[1.15em] font-normal text-gradient">name</span> on them
            </>
          )
        }
        description={
          similarId
            ? "Neighbours in sound and genre, pulled from your catalogue and fresh discovery seeds."
            : active.data?.cold_start
              ? "Still learning your taste — save songs, like picks, or choose a few seed genres below."
              : `Blending your last ${active.data?.short_term_days ?? 28} days with the longer arc of who you are.`
        }
        actions={
          similarId ? (
            <button type="button" onClick={clearSimilar} className={buttonVariants({ variant: "secondary" })}>
              Back to For You
            </button>
          ) : (
            <Link to="/discover" className={buttonVariants({ variant: "cta" })}>
              <Sparkles data-icon="inline-start" /> Discover more
            </Link>
          )
        }
      />

      {!similarId && (
        <section className="powder relative mb-8 overflow-hidden rounded-3xl border border-lavender/15 bg-satin-royal p-5 shadow-whip sm:p-6">
          <HairWaves className="absolute inset-0 h-full w-full opacity-40" />
          <Rose className="absolute -top-10 -right-8 size-28 opacity-80" />
          <div className="relative">
            <p className="font-script text-3xl text-cream">seed your taste</p>
            <p className="mt-1 max-w-xl text-sm text-lavender">
              Tap a few moods. Tunewise uses them when listening history is still thin — you can change them anytime.
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              {SEED_GENRES.map((g) => {
                const on = picked.includes(g);
                return (
                  <button
                    key={g}
                    type="button"
                    disabled={seed.isPending}
                    onClick={() => toggleGenre(g)}
                    className={cn(
                      "rounded-full px-3.5 py-1.5 text-sm font-bold ring-1 transition-colors",
                      on
                        ? "bg-cta text-white ring-lavender/30"
                        : "bg-deep-purple/55 text-cream ring-lavender/20 hover:bg-deep-purple",
                    )}
                  >
                    {g}
                  </button>
                );
              })}
            </div>
          </div>
        </section>
      )}

      {active.isPending ? (
        <GridSkeleton />
      ) : items.length === 0 ? (
        <EmptyState
          icon={HeartHandshake}
          title="No picks yet"
          description="Search and save a few songs, or choose seed genres above. Then come back for a fresh mix."
          action={
            <Link to="/discover" className={buttonVariants({ variant: "cta" })}>
              Discover music
            </Link>
          }
        />
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 sm:gap-4 xl:grid-cols-4">
          {items.map((item) => (
            <RecommendationCard
              key={item.song.id}
              item={item}
              queue={queue}
              context={similarId ? "similar" : "recommendations"}
            />
          ))}
        </div>
      )}

      <p className="relative mt-10 flex items-start gap-2 text-sm text-subtle">
        <Petal className="mt-0.5 size-4 shrink-0 opacity-70" />
        Skips stay neutral. Only an explicit like or “not interested” reshapes what shows up next.
      </p>
    </>
  );
}
