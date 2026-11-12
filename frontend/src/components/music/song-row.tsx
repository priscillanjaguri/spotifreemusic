import { Check, HardDriveUpload, Loader2, Pause, Play, Plus, Trash2 } from "lucide-react";
import type { ReactNode } from "react";
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

export function OwnFileBadge() {
  return (
    <Tooltip>
      <TooltipTrigger render={<span className="shrink-0" />}>
        <Badge variant="genre" className="gap-1">
          <HardDriveUpload className="size-3" />
          Your file
        </Badge>
      </TooltipTrigger>
      <TooltipContent>Uploaded to My Library. Only you can see and play it.</TooltipContent>
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
    | { kind: "remove"; pending: boolean; onRemove: () => void; label?: string };
  linkFacets?: boolean;
  badges?: ReactNode;
};

/** Lets a whole row or tile start playback, while its own buttons and links keep their behaviour. */
export function onSurfaceClick(event: React.MouseEvent, play: () => void) {
  if ((event.target as HTMLElement).closest("button, a, input, [role=menuitem]")) return;
  if (window.getSelection()?.toString()) return;
  play();
}

export function SongRow({ song, queue, index, meta, action, linkFacets, badges }: SongRowProps) {
  const player = usePlayer();
  const isCurrent = player.current?.id === song.id;
  const isPlaying = isCurrent && player.isPlaying;
  const playable = Boolean(song.playback);

  const onPlay = () => (isCurrent ? player.toggle() : player.play(song, queue));

  return (
    <div className="@container">
      <div
        onClick={playable ? (e) => onSurfaceClick(e, onPlay) : undefined}
        className={cn(
          "group flex items-center gap-3 px-3 py-2.5 transition-colors @md:px-4",
          playable && "cursor-pointer",
          isCurrent ? "bg-accent/80" : "hover:bg-surface-raised",
        )}
      >
        {index !== undefined && (
          <span className="hidden w-6 shrink-0 text-right text-sm tabular-nums text-subtle @md:block">
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
              "absolute inset-0 grid place-items-center rounded-xl bg-grape/40 text-white backdrop-blur-[1px] transition-opacity focus-visible:opacity-100 disabled:cursor-not-allowed",
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
            <p className={cn("min-w-0 truncate font-bold", isCurrent ? "text-accent-foreground" : "text-heading")}>{song.title}</p>
            {song.data_source === "mock_dev" && <MockBadge />}
            {song.data_source === "user_provided" && !badges && <OwnFileBadge />}
            {badges}
          </div>
          <p className="truncate text-sm text-muted-foreground">
            {linkFacets
              ? song.artists.map((a, i) => (
                  <span key={a.id}>
                    {i > 0 && ", "}
                    <Link to={`/collection?artist=${a.id}`} className="hover:text-accent-foreground hover:underline">
                      {a.name}
                    </Link>
                  </span>
                ))
              : artistNames(song.artists)}
            {meta && <span className="text-subtle @3xl:hidden"> · {meta}</span>}
          </p>
        </div>

        <div className="hidden w-44 min-w-0 shrink-0 @xl:block @5xl:w-56">
          {song.album ? (
            linkFacets ? (
              <Link
                to={`/collection?album=${song.album.id}`}
                className="block truncate text-sm text-muted-foreground hover:text-accent-foreground hover:underline"
              >
                {song.album.title}
              </Link>
            ) : (
              <p className="truncate text-sm text-muted-foreground">{song.album.title}</p>
            )
          ) : (
            <p className="text-sm text-subtle">Single</p>
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

        {meta && <span className="hidden w-24 shrink-0 text-right text-xs text-subtle @3xl:block">{meta}</span>}
        <span className="hidden w-12 shrink-0 text-right text-sm tabular-nums text-subtle @md:block">
          {formatDuration(song.duration_ms)}
        </span>

        {action?.kind === "add" && (
          <Button
            size="icon-sm"
            variant={action.saved ? "secondary" : "ghost"}
            className={cn("shrink-0 rounded-full", action.saved ? "bg-accent text-accent-foreground" : "text-muted-foreground hover:text-accent-foreground")}
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
            className="shrink-0 rounded-full text-subtle hover:bg-rose/10 hover:text-rose lg:opacity-0 lg:group-hover:opacity-100 lg:focus-visible:opacity-100"
            onClick={action.onRemove}
            disabled={action.pending}
            aria-label={action.label ?? `Remove ${song.title} from collection`}
          >
            {action.pending ? <Loader2 className="animate-spin" /> : <Trash2 />}
          </Button>
        )}
      </div>
    </div>
  );
}
