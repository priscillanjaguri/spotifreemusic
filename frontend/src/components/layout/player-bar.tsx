import { Loader2, Pause, Play, Scale, SkipBack, SkipForward, Volume1, Volume2, VolumeX, X } from "lucide-react";
import { CoverArt } from "@/components/music/cover-art";
import { MockBadge } from "@/components/music/song-row";
import { Button } from "@/components/ui/button";
import { artistNames, formatDuration } from "@/lib/format";
import { usePlayer } from "@/lib/player";
import { cn } from "@/lib/utils";

function Range({
  value,
  max,
  onChange,
  label,
  className,
}: {
  value: number;
  max: number;
  onChange: (v: number) => void;
  label: string;
  className?: string;
}) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <input
      type="range"
      aria-label={label}
      min={0}
      max={max || 1}
      step={0.01}
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
      className={cn("tw-range h-1.5 w-full cursor-pointer appearance-none rounded-full bg-heather", className)}
      style={{ background: `linear-gradient(90deg, var(--color-lavender), var(--color-magenta) ${pct}%, var(--color-heather) ${pct}%)` }}
    />
  );
}

export function PlayerBar() {
  const p = usePlayer();
  const song = p.current;
  if (!song) return null;

  const PlayIcon = p.isLoading ? Loader2 : p.isPlaying ? Pause : Play;
  const VolumeIcon = p.volume === 0 ? VolumeX : p.volume < 0.5 ? Volume1 : Volume2;
  const license = song.playback?.license_url;

  return (
    <div
      role="region"
      aria-label="Now playing"
      className="fixed inset-x-2 bottom-[4.5rem] z-40 rounded-2xl border border-iris/40 bg-eggplant/90 shadow-glow backdrop-blur-xl lg:inset-x-auto lg:bottom-4 lg:left-[17rem] lg:right-4"
    >
      <div className="absolute inset-x-3 top-0 lg:hidden">
        <div
          className="h-0.5 rounded-full bg-gradient-to-r from-lavender to-magenta"
          style={{ width: `${p.duration ? (p.position / p.duration) * 100 : 0}%` }}
        />
      </div>
      <div className="flex items-center gap-3 p-2.5 lg:grid lg:grid-cols-[1fr_minmax(0,1.4fr)_1fr] lg:gap-6 lg:px-4">
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <CoverArt src={song.cover_url} seed={song.id} title={song.title} className="size-11" />
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <p className="truncate text-sm font-semibold text-lilac">{song.title}</p>
              {song.data_source === "mock_dev" && <MockBadge />}
            </div>
            <p className="truncate text-xs text-muted-foreground">
              {artistNames(song.artists)}
              {license && (
                <>
                  {" · "}
                  <a
                    href={license}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-lavender/80 hover:text-lavender hover:underline"
                  >
                    <Scale className="size-3" /> Licence
                  </a>
                </>
              )}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1 lg:flex-col lg:gap-1.5">
          <div className="flex items-center gap-1 lg:gap-2">
            <Button size="icon-sm" variant="ghost" className="hidden text-mauve hover:text-lilac sm:inline-flex" onClick={p.previous} aria-label="Previous">
              <SkipBack className="fill-current" />
            </Button>
            <Button
              size="icon"
              variant="cta"
              className="rounded-full"
              onClick={p.toggle}
              aria-label={p.isPlaying ? "Pause" : "Play"}
            >
              <PlayIcon className={cn("fill-current", p.isLoading && "animate-spin fill-none")} />
            </Button>
            <Button size="icon-sm" variant="ghost" className="text-mauve hover:text-lilac" onClick={p.next} aria-label="Next">
              <SkipForward className="fill-current" />
            </Button>
          </div>
          <div className="hidden w-full items-center gap-2 text-[11px] tabular-nums text-dusk lg:flex">
            <span className="w-9 text-right">{formatDuration(p.position * 1000)}</span>
            <Range value={p.position} max={p.duration} onChange={p.seek} label="Seek" />
            <span className="w-9">{formatDuration(p.duration * 1000)}</span>
          </div>
        </div>

        <div className="hidden items-center justify-end gap-2 lg:flex">
          <Button
            size="icon-sm"
            variant="ghost"
            className="text-mauve hover:text-lilac"
            onClick={() => p.setVolume(p.volume === 0 ? 0.8 : 0)}
            aria-label={p.volume === 0 ? "Unmute" : "Mute"}
          >
            <VolumeIcon />
          </Button>
          <Range value={p.volume} max={1} onChange={p.setVolume} label="Volume" className="max-w-28" />
          <Button size="icon-sm" variant="ghost" className="text-dusk hover:text-lilac" onClick={p.stop} aria-label="Close player">
            <X />
          </Button>
        </div>
      </div>
    </div>
  );
}
