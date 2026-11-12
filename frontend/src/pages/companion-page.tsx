import { Coffee, MoonStar, Sparkles, SunMedium, Waves, Zap } from "lucide-react";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { HairWaves, Petal, Rose } from "@/components/decor";
import { PageHeader } from "@/components/layout/app-shell";
import { CoverArt } from "@/components/music/cover-art";
import { RecommendationCard } from "@/components/music/recommendation-card";
import { EmptyState, ErrorState } from "@/components/states";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { useDailyCompanion, useSetCompanionMood } from "@/lib/companion";
import { artistNames } from "@/lib/format";
import { usePlayer } from "@/lib/player";
import type { CompanionMood } from "@/lib/types";
import { cn } from "@/lib/utils";

const MOOD_META: Record<
  CompanionMood,
  { label: string; blurb: string; icon: typeof Sparkles }
> = {
  soft: { label: "Soft", blurb: "tender & warm", icon: Coffee },
  dreamy: { label: "Dreamy", blurb: "haze & float", icon: MoonStar },
  focus: { label: "Focus", blurb: "deep work", icon: Waves },
  energy: { label: "Energy", blurb: "move & glow", icon: Zap },
  chill: { label: "Chill", blurb: "easy evening", icon: SunMedium },
  glow: { label: "Glow", blurb: "main character", icon: Sparkles },
};

export function CompanionPage() {
  const [mood, setMood] = useState<CompanionMood | null>(null);
  const companion = useDailyCompanion(mood, 12);
  const setMoodMut = useSetCompanionMood();
  const player = usePlayer();

  const queue = useMemo(
    () => companion.data?.playlist.map((i) => i.song) ?? [],
    [companion.data],
  );

  const pickMood = (next: CompanionMood) => {
    setMood(next);
    setMoodMut.mutate(next);
  };

  if (companion.isError) {
    return (
      <>
        <PageHeader eyebrow="daily companion" title="A mix for right now" />
        <ErrorState error={companion.error} onRetry={() => void companion.refetch()} />
      </>
    );
  }

  const data = companion.data;

  return (
    <>
      <PageHeader
        eyebrow="daily companion"
        title={
          data ? (
            <>
              {data.greeting.split(",")[0]},{" "}
              <span className="font-script text-[1.15em] font-normal text-gradient">
                {data.greeting.includes(",") ? data.greeting.split(",").slice(1).join(",").trim() : "friend"}
              </span>
            </>
          ) : (
            "A mix for right now"
          )
        }
        description={data?.briefing ?? "Gathering today’s colours from your taste and recent listens…"}
        actions={
          queue.length > 0 && (
            <Button
              variant="cta"
              size="lg"
              onClick={() => player.play(queue[0]!, queue)}
            >
              Play today’s mix
            </Button>
          )
        }
      />

      <section className="powder relative overflow-hidden rounded-[2rem] border border-lavender/15 bg-satin-royal p-5 shadow-whip-lg sm:p-6">
        <HairWaves className="absolute inset-0 opacity-40" />
        <Rose className="absolute -right-8 top-0 size-28 opacity-70" />
        <div className="relative">
          <p className="font-script text-2xl text-highlight">how are you feeling?</p>
          <p className="mt-1 max-w-xl text-sm text-muted-foreground">
            Pick a mood to steer the recommender. It blends with your listening history — never invents a dislike.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            {(Object.keys(MOOD_META) as CompanionMood[]).map((key) => {
              const meta = MOOD_META[key];
              const Icon = meta.icon;
              const active = (setMoodMut.data?.mood ?? mood) === key;
              return (
                <button
                  key={key}
                  type="button"
                  onClick={() => pickMood(key)}
                  className={cn(
                    "gloss inline-flex items-center gap-2 rounded-full px-3.5 py-2 text-sm font-bold ring-1 transition-all",
                    active
                      ? "bg-cta text-white ring-lavender/40 shadow-whip"
                      : "bg-deep-purple/50 text-lavender ring-lavender/15 hover:bg-deep-purple hover:text-cream",
                  )}
                >
                  <Icon className="size-4" />
                  {meta.label}
                  <span className="hidden text-xs font-semibold opacity-80 sm:inline">{meta.blurb}</span>
                </button>
              );
            })}
          </div>
        </div>
      </section>

      <div className="mt-8 grid gap-5 lg:grid-cols-[1.2fr_0.8fr]">
        <section>
          <div className="mb-4 flex items-end justify-between">
            <h2 className="font-display text-3xl font-semibold text-heading">Today’s playlist</h2>
            {data && (
              <Badge variant="highlight" className="capitalize">
                {data.mode.replaceAll("_", " ")}
              </Badge>
            )}
          </div>
          {companion.isPending ? (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              {Array.from({ length: 6 }, (_, i) => (
                <Skeleton key={i} className="aspect-[3/4] rounded-3xl bg-accent" />
              ))}
            </div>
          ) : queue.length === 0 ? (
            <EmptyState
              icon={Sparkles}
              title="Companion is warming up"
              description="Save a few songs, play something from Discover, or pick seed genres on For You."
              action={
                <Link to="/recommendations" className={buttonVariants({ variant: "cta" })}>
                  Open For You
                </Link>
              }
            />
          ) : (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
              {data!.playlist.map((item) => (
                <RecommendationCard key={item.song.id} item={item} queue={queue} context="daily_companion" />
              ))}
            </div>
          )}
        </section>

        <aside className="space-y-5">
          <section className="rounded-3xl border border-border bg-card satin p-5 shadow-whip">
            <p className="font-script text-2xl text-highlight">today’s notes</p>
            <ul className="mt-3 space-y-3">
              {(data?.insights ?? []).map((insight) => (
                <li key={insight.code} className="flex gap-2 text-sm text-muted-foreground">
                  <Petal className="mt-0.5 size-3.5 shrink-0" />
                  <span>{insight.label}</span>
                </li>
              ))}
              {companion.isPending &&
                Array.from({ length: 3 }, (_, i) => <Skeleton key={i} className="h-4 w-full bg-accent" />)}
            </ul>
            <Link
              to="/analytics"
              className="mt-4 inline-flex text-sm font-bold text-accent-foreground hover:text-highlight"
            >
              See full analytics →
            </Link>
          </section>

          {data?.spotlight && (
            <section className="overflow-hidden rounded-3xl border border-lavender/15 bg-satin-deep p-5">
              <p className="font-script text-2xl text-cream">spotlight</p>
              <button
                type="button"
                className="mt-3 flex w-full items-center gap-3 text-left"
                onClick={() =>
                  data.spotlight?.song.playback &&
                  player.play(data.spotlight.song, [data.spotlight.song])
                }
              >
                <CoverArt
                  src={data.spotlight.song.cover_url}
                  seed={data.spotlight.song.id}
                  title={data.spotlight.song.title}
                  className="size-16"
                />
                <div className="min-w-0">
                  <Badge variant="genre" className="mb-1 capitalize">
                    {data.spotlight.kind.replaceAll("_", " ")}
                  </Badge>
                  <p className="truncate font-bold text-cream">{data.spotlight.song.title}</p>
                  <p className="truncate text-xs text-lavender/80">
                    {artistNames(data.spotlight.song.artists)}
                  </p>
                  <p className="mt-1 truncate text-xs text-lavender/70">{data.spotlight.label}</p>
                </div>
              </button>
            </section>
          )}
        </aside>
      </div>
    </>
  );
}
