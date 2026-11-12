import { Heart, Loader2, Pause, Play, Sparkles, ThumbsDown } from "lucide-react";
import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { artistNames } from "@/lib/format";
import { usePlayer } from "@/lib/player";
import { useFeedback } from "@/lib/recommendations";
import type { RecommendationItem, Song } from "@/lib/types";
import { cn } from "@/lib/utils";
import { CoverArt } from "./cover-art";
import { MockBadge, onSurfaceClick } from "./song-row";

export function RecommendationCard({
  item,
  queue,
  context = "recommendations",
}: {
  item: RecommendationItem;
  queue: Song[];
  context?: string;
}) {
  const { song, explanations } = item;
  const player = usePlayer();
  const feedback = useFeedback(context);
  const isCurrent = player.current?.id === song.id;
  const isPlaying = isCurrent && player.isPlaying;
  const playable = Boolean(song.playback);
  const onPlay = () => (isCurrent ? player.toggle() : player.play(song, queue));
  const pending = feedback.isPending && feedback.variables?.song.id === song.id;

  return (
    <div
      onClick={playable ? (e) => onSurfaceClick(e, onPlay) : undefined}
      className={cn(
        playable && "cursor-pointer",
        "group satin relative flex flex-col rounded-3xl border border-border bg-card p-3 shadow-whip transition-all hover:-translate-y-1 hover:bg-surface-raised hover:shadow-whip-lg",
        isCurrent && "ring-2 ring-wisteria/60",
      )}
    >
      <div className="relative">
        <CoverArt
          src={song.cover_url}
          seed={song.id}
          title={song.title}
          className="aspect-square w-full rounded-2xl"
          iconClassName="size-1/4"
        />
        <button
          type="button"
          onClick={onPlay}
          disabled={!playable}
          aria-label={isPlaying ? `Pause ${song.title}` : `Play ${song.title}`}
          className={cn(
            "gloss absolute right-2 bottom-2 grid size-11 place-items-center rounded-full bg-cta text-white shadow-polish transition-all disabled:hidden",
            isCurrent
              ? "opacity-100"
              : "translate-y-2 opacity-0 group-hover:translate-y-0 group-hover:opacity-100 focus-visible:opacity-100",
          )}
        >
          {isCurrent && player.isLoading ? (
            <Loader2 className="size-5 animate-spin" />
          ) : isPlaying ? (
            <Pause className="size-5 fill-current" />
          ) : (
            <Play className="ml-0.5 size-5 fill-current" />
          )}
        </button>
      </div>

      <div className="mt-3 flex min-h-0 flex-1 flex-col px-1 pb-1">
        <p className={cn("truncate font-bold", isCurrent ? "text-accent-foreground" : "text-heading")}>{song.title}</p>
        <p className="truncate text-sm text-muted-foreground">{artistNames(song.artists)}</p>

        <div className="mt-2 flex min-h-[1.5rem] flex-wrap gap-1.5">
          {explanations.slice(0, 2).map((chip) => (
            <Badge
              key={chip.code + chip.label}
              variant="highlight"
              className="max-w-full truncate text-[11px] font-semibold normal-case"
            >
              <Sparkles className="mr-1 inline size-3 opacity-80" />
              {chip.label}
            </Badge>
          ))}
          {song.data_source === "mock_dev" && <MockBadge />}
        </div>

        <div className="mt-3 flex items-center gap-1">
          <Button
            size="icon-sm"
            variant="ghost"
            className="rounded-full text-orchid-glow hover:bg-lilac/15 hover:text-highlight"
            disabled={pending}
            title="Like"
            aria-label={`Like ${song.title}`}
            onClick={() => feedback.mutate({ song, action: "like" })}
          >
            {pending && feedback.variables?.action === "like" ? <Loader2 className="animate-spin" /> : <Heart className="size-4" />}
          </Button>
          <Button
            size="icon-sm"
            variant="ghost"
            className="rounded-full text-subtle hover:bg-rose/10 hover:text-rose"
            disabled={pending}
            title="Not interested"
            aria-label={`Not interested in ${song.title}`}
            onClick={() => feedback.mutate({ song, action: "not_interested" })}
          >
            {pending && feedback.variables?.action === "not_interested" ? (
              <Loader2 className="animate-spin" />
            ) : (
              <ThumbsDown className="size-4" />
            )}
          </Button>
          <Link
            to={`/recommendations?similar=${song.id}`}
            className="ml-auto text-xs font-bold text-accent-foreground hover:text-highlight"
            onClick={(e) => e.stopPropagation()}
          >
            More like this
          </Link>
        </div>
      </div>
    </div>
  );
}
