import { Check, Loader2, Pause, Play, Plus, Trash2 } from "lucide-react";
import { Link } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { artistNames, formatDuration } from "@/lib/format";
import { usePlayer } from "@/lib/player";
import type { Song } from "@/lib/types";
import { cn } from "@/lib/utils";
import { CoverArt } from "./cover-art";
import { Equalizer } from "./equalizer";

export function MockBadge() {
  return (
    <Tooltip>
      <TooltipTrigger render={<span className="shrink-0" />}>
        <Badge variant="mock">Sample</Badge>
      </TooltipTrigger>
      <TooltipContent>Invented development data, not a real recording</TooltipContent>
    </Tooltip>
  );
}

type SongRowProps = {
  song: Song;
  queue: Song[];
  index?: number;
  meta?: string;
  action?:
    | { kind: "add"; saved: boolean; pending: boolean; onAdd: () => void }
    | { kind: "remove"; pending: boolean; onRemove: () => void };
  linkFacets?: boolean;
};

export function SongRow({ song, queue, index, meta, action, linkFacets }: SongRowProps) {
  const player = usePlayer();
  const isCurrent = player.current?.id === song.id;
  const isPlaying = isCurrent && player.isPlaying;
  const playable = Boolean(song.playback);

  const onPlay = () => (isCurrent ? player.toggle() : player.play(song, queue));

  return (
    <div className="@container">
      <div
        className={cn(
          "group flex items-center gap-3 px-3 py-2.5 transition-colors @md:px-4",
          isCurrent ? "bg-accent/70" : "hover:bg-accent/40",
        )}
      >
        {index !== undefined && (
          <span className="hidden w-6 shrink-0 text-right text-sm tabular-nums text-dusk @md:block">
            {isPlaying ? <Equalizer className="ml-auto" /> : index + 1}
          </span>
        )}

        <div className="relative">
          <CoverArt src={song.cover_url} seed={song.id} title={song.title} className="size-11 @md:size-12" />
          <button
            type="button"
            onClick={onPlay}
            disabled={!playable}
            aria-label={isPlaying ? `Pause ${song.title}` : `Play ${song.title}`}
            title={playable ? undefined : "No playable stream for this song"}
            className={cn(
              "absolute inset-0 grid place-items-center rounded-lg bg-night/60 text-white transition-opacity focus-visible:opacity-100 disabled:cursor-not-allowed",
              isCurrent ? "opacity-100" : "opacity-0 group-hover:opacity-100",
              !playable && "group-hover:opacity-60",
            )}
          >
            {isCurrent && player.isLoading ? (
              <Loader2 className="size-5 animate-spin" />
            ) : isPlaying ? (
              <Pause className="size-5 fill-current" />
            ) : (
              <Play className="size-5 fill-current" />
            )}
          </button>
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className={cn("min-w-0 truncate font-medium", isCurrent ? "text-magenta" : "text-lilac")}>{song.title}</p>
            {song.data_source === "mock_dev" && <MockBadge />}
          </div>
          <p className="truncate text-sm text-muted-foreground">
            {linkFacets
              ? song.artists.map((a, i) => (
                  <span key={a.id}>
                    {i > 0 && ", "}
                    <Link to={`/collection?artist=${a.id}`} className="hover:text-lavender hover:underline">
                      {a.name}
                    </Link>
                  </span>
                ))
              : artistNames(song.artists)}
            {meta && <span className="text-dusk @3xl:hidden"> · {meta}</span>}
          </p>
        </div>

        <div className="hidden w-44 min-w-0 shrink-0 @xl:block @5xl:w-56">
          {song.album ? (
            linkFacets ? (
              <Link
                to={`/collection?album=${song.album.id}`}
                className="block truncate text-sm text-mauve hover:text-lavender hover:underline"
              >
                {song.album.title}
              </Link>
            ) : (
              <p className="truncate text-sm text-mauve">{song.album.title}</p>
            )
          ) : (
            <p className="text-sm text-dusk">Single</p>
          )}
        </div>

        <div className="hidden w-40 shrink-0 flex-wrap gap-1 @4xl:flex">
          {song.genres.slice(0, 2).map((g) =>
            linkFacets ? (
              <Badge key={g} variant="genre" render={<Link to={`/collection?genre=${encodeURIComponent(g)}`} />}>
                {g}
              </Badge>
            ) : (
              <Badge key={g} variant="genre">
                {g}
              </Badge>
            ),
          )}
        </div>

        {meta && <span className="hidden w-24 shrink-0 text-right text-xs text-dusk @3xl:block">{meta}</span>}
        <span className="hidden w-12 shrink-0 text-right text-sm tabular-nums text-dusk @md:block">
          {formatDuration(song.duration_ms)}
        </span>

        {action?.kind === "add" && (
          <Button
            size="icon-sm"
            variant={action.saved ? "secondary" : "ghost"}
            className={cn("shrink-0 rounded-full", action.saved ? "text-lavender" : "text-mauve hover:text-magenta")}
            onClick={action.onAdd}
            disabled={action.saved || action.pending}
            aria-label={action.saved ? `${song.title} is in your collection` : `Add ${song.title} to collection`}
          >
            {action.pending ? <Loader2 className="animate-spin" /> : action.saved ? <Check /> : <Plus />}
          </Button>
        )}
        {action?.kind === "remove" && (
          <Button
            size="icon-sm"
            variant="ghost"
            className="shrink-0 rounded-full text-dusk hover:bg-berry/15 hover:text-berry lg:opacity-0 lg:group-hover:opacity-100 lg:focus-visible:opacity-100"
            onClick={action.onRemove}
            disabled={action.pending}
            aria-label={`Remove ${song.title} from collection`}
          >
            {action.pending ? <Loader2 className="animate-spin" /> : <Trash2 />}
          </Button>
        )}
      </div>
    </div>
  );
}
