import { Loader2, Pause, Play } from "lucide-react";
import { artistNames } from "@/lib/format";
import { usePlayer } from "@/lib/player";
import type { Song } from "@/lib/types";
import { cn } from "@/lib/utils";
import { CoverArt } from "./cover-art";
import { MockBadge } from "./song-row";

/** Spotify-style tile: big cover, floating play button on hover. */
export function SongCard({ song, queue, meta }: { song: Song; queue: Song[]; meta?: string }) {
  const player = usePlayer();
  const isCurrent = player.current?.id === song.id;
  const isPlaying = isCurrent && player.isPlaying;
  const playable = Boolean(song.playback);

  return (
    <div
      className={cn(
        "group relative rounded-3xl border border-white/80 bg-white/70 p-3 shadow-whip transition-all hover:-translate-y-1 hover:bg-white hover:shadow-whip-lg",
        isCurrent && "ring-2 ring-wisteria/60",
      )}
    >
      <div className="relative">
        <CoverArt src={song.cover_url} seed={song.id} title={song.title} className="aspect-square w-full rounded-2xl" iconClassName="size-1/4" />
        <button
          type="button"
          onClick={() => (isCurrent ? player.toggle() : player.play(song, queue))}
          disabled={!playable}
          aria-label={isPlaying ? `Pause ${song.title}` : `Play ${song.title}`}
          className={cn(
            "gloss absolute right-2 bottom-2 grid size-11 place-items-center rounded-full bg-cta text-white shadow-polish transition-all disabled:hidden",
            isCurrent ? "opacity-100" : "translate-y-2 opacity-0 group-hover:translate-y-0 group-hover:opacity-100 focus-visible:opacity-100",
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
      <div className="mt-3 px-1 pb-1">
        <p className={cn("truncate font-bold", isCurrent ? "text-purple" : "text-heading")}>{song.title}</p>
        <p className="truncate text-sm text-muted-foreground">{artistNames(song.artists)}</p>
        <div className="mt-2 flex items-center justify-between gap-2">
          {meta && <span className="text-xs text-subtle">{meta}</span>}
          {song.data_source === "mock_dev" && <MockBadge />}
        </div>
      </div>
    </div>
  );
}
