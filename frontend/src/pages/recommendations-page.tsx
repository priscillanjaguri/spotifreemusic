import { HeartHandshake, Sparkles } from "lucide-react";
import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { ButterflyDrift, MOOD, MoodAccent, MoodPhoto, Petal, PhotoCollage, PhotoHero } from "@/components/decor";
import { Logo } from "@/components/layout/logo";
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
        <PhotoHero src={MOOD.collageFull} position="center 20%" dense>
          <Logo className="mb-3" />
          <p className="font-script text-2xl text-orchid-glow">for you</p>
          <h1 className="mt-1 font-display text-4xl font-semibold text-cream">Picks with your name on them</h1>
        </PhotoHero>
        <div className="mt-6">
          <ErrorState error={active.error} onRetry={() => void active.refetch()} />
        </div>
      </>
    );
  }

  return (
    <>
      <section className="relative overflow-hidden rounded-[1.75rem] sm:rounded-[2rem] min-h-[20rem] sm:min-h-[22rem]">
        <PhotoCollage opacity={1} drift />
        <div
          aria-hidden
          className="absolute inset-0 bg-gradient-to-t from-[#0c0612]/92 via-[#1a0b28]/55 to-[#2a1040]/3"
        />
        <div
          aria-hidden
          className="absolute inset-0 bg-gradient-to-r from-[#160a1f]/75 via-transparent to-[#3a1050]/35"
        />
        <ButterflyDrift className="opacity-55" />
        <div className="relative z-10 flex h-full min-h-[20rem] flex-col justify-end p-5 sm:min-h-[22rem] sm:p-7 lg:p-8">
          <Logo className="mb-3" />
          <p className="font-script text-2xl text-orchid-glow">for you</p>
          <h1 className="mt-1 font-display text-4xl font-semibold tracking-tight text-cream sm:text-5xl">
            {similarId ? (
              <>
                More like <span className="font-script text-[1.15em] font-normal text-gradient">this</span>
              </>
            ) : (
              <>
                Picks with your <span className="font-script text-[1.15em] font-normal text-gradient">name</span> on them
              </>
            )}
          </h1>
          <p className="mt-2 max-w-xl text-sm text-lavender/95">
            {similarId
              ? "Neighbours in sound and genre, pulled from your catalogue and fresh discovery seeds."
              : active.data?.cold_start
                ? "Still learning your taste — save songs, like picks, or choose a few seed genres below."
                : `Blending your last ${active.data?.short_term_days ?? 28} days with the longer arc of who you are.`}
          </p>
          <div className="mt-5">
            {similarId ? (
              <button type="button" onClick={clearSimilar} className={buttonVariants({ variant: "secondary" })}>
                Back to For You
              </button>
            ) : (
              <Link to="/discover" className={buttonVariants({ variant: "cta" })}>
                <Sparkles data-icon="inline-start" /> Discover more
              </Link>
            )}
          </div>
        </div>
      </section>

      {!similarId && (
        <section className="relative mt-8 mb-8 overflow-hidden rounded-[1.75rem] p-5 sm:p-6 ring-1 ring-orchid-glow/35">
          <MoodPhoto src={MOOD.lookingUp} opacity={0.5} position="center 25%" className="inset-0" />
          <MoodAccent src={MOOD.butterflyNeon} side="right" className="opacity-60" />
          <div
            aria-hidden
            className="absolute inset-0 bg-gradient-to-r from-[#6a2098]/75 via-[#4a1870]/65 to-[#2a0c48]/55"
          />
          <div className="relative">
            <p className="font-script text-3xl text-cream">seed your taste</p>
            <p className="mt-1 max-w-xl text-sm text-lavender">
              Tap a few moods. Spotifree uses them when listening history is still thin — you can change them anytime.
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
                        : "bg-[#5a1a78]/65 text-cream ring-orchid-glow/30 hover:bg-[#6a2098]",
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

      <div className="relative overflow-hidden rounded-[2rem] p-4 ring-1 ring-orchid-glow/25 sm:p-5">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 bg-gradient-to-b from-[#5a1a78]/35 via-[#3a1058]/45 to-[#1a0b28]/55"
        />
        <div className="relative">
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

          <p className="relative mt-10 flex items-start gap-2 text-sm text-lavender/80">
            <Petal className="mt-0.5 size-4 shrink-0 opacity-70" />
            Skips stay neutral. Only an explicit like or “not interested” reshapes what shows up next.
          </p>
        </div>
      </div>
    </>
  );
}
