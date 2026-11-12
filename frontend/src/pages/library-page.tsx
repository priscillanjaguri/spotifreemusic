import {
  AlertTriangle,
  AudioLines,
  Ban,
  CheckCircle2,
  Copy,
  FolderHeart,
  HardDrive,
  Loader2,
  Play,
  RotateCw,
  ShieldCheck,
  Sparkles,
  Upload,
} from "lucide-react";
import { useRef, useState } from "react";
import { Petal, Rose } from "@/components/decor";
import { PageHeader } from "@/components/layout/app-shell";
import { SongRow } from "@/components/music/song-row";
import { EmptyState, ErrorState, SongListSkeleton } from "@/components/states";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { formatBytes, plural } from "@/lib/format";
import { type QueueItem, useDeleteUpload, useLibrary, useUploadQueue } from "@/lib/library";
import { usePlayer } from "@/lib/player";
import type { LibraryLimits, LibraryUpload, Song } from "@/lib/types";
import { cn } from "@/lib/utils";

const FORMATS = "MP3, M4A/AAC, FLAC, OGG or WAV";

function Dropzone({
  onFiles,
  accept,
  limits,
  compact,
}: {
  onFiles: (files: FileList) => void;
  accept: string;
  limits?: LibraryLimits;
  compact: boolean;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const depth = useRef(0);
  const open = () => input.current?.click();

  return (
    <section
      role="button"
      tabIndex={0}
      aria-label="Add music files: drop them here or press to choose"
      onClick={open}
      onKeyDown={(e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), open())}
      onDragEnter={(e) => {
        e.preventDefault();
        depth.current += 1;
        setDragging(true);
      }}
      onDragOver={(e) => e.preventDefault()}
      onDragLeave={() => {
        depth.current = Math.max(0, depth.current - 1);
        if (depth.current === 0) setDragging(false);
      }}
      onDrop={(e) => {
        e.preventDefault();
        depth.current = 0;
        setDragging(false);
        if (e.dataTransfer.files.length) onFiles(e.dataTransfer.files);
      }}
      className={cn(
        "powder glass group relative cursor-pointer overflow-hidden rounded-[2rem] border-2 border-dashed border-white/20 text-center transition-all outline-none focus-visible:ring-3 focus-visible:ring-ring/50",
        compact ? "px-6 py-7" : "px-6 py-12 sm:py-16",
        dragging
          ? "scale-[1.01] border-orchid-glow bg-satin-amethyst shadow-glow"
          : "border-lavender/25 bg-satin-royal hover:border-lavender/45",
      )}
    >
      <Rose className={cn("pointer-events-none absolute -right-10 -bottom-12 opacity-80 drop-shadow-xl", compact ? "size-32" : "size-48")} />
      <Petal className="pointer-events-none absolute top-6 left-[8%] size-6 rotate-[-20deg] opacity-60" />
      <Petal className="pointer-events-none absolute top-[40%] left-[22%] hidden size-4 rotate-[60deg] opacity-40 sm:block" />
      <input
        ref={input}
        type="file"
        multiple
        accept={`audio/*,${accept}`}
        className="sr-only"
        tabIndex={-1}
        onClick={(e) => e.stopPropagation()}
        onChange={(e) => {
          if (e.target.files?.length) onFiles(e.target.files);
          e.target.value = "";
        }}
      />
      <div className={cn("relative flex items-center gap-5", compact ? "flex-row justify-center text-left" : "flex-col")}>
        <span className="gloss grid size-16 shrink-0 place-items-center rounded-full bg-cta text-white shadow-polish transition-transform group-hover:scale-105">
          <Upload className="size-7" />
        </span>
        <div>
          <h2 className={cn("font-display font-semibold text-heading", compact ? "text-2xl" : "text-3xl sm:text-4xl")}>
            {dragging ? "Let go to add them" : (
              <>
                <span className="hidden sm:inline">Drop your music here</span>
                <span className="sm:hidden">Add music from your device</span>
              </>
            )}
          </h2>
          <p className="mt-1.5 text-sm text-muted-foreground">
            <span className="hidden sm:inline">or <span className="font-bold text-lavender underline-offset-4 group-hover:underline">choose files</span> · </span>
            {FORMATS} · up to {limits?.max_file_mb ?? 200} MB each
          </p>
        </div>
      </div>
    </section>
  );
}

const QUEUE_LOOK: Record<QueueItem["status"], { icon: typeof Upload; tone: string; label: string }> = {
  queued: { icon: Loader2, tone: "text-subtle", label: "Waiting" },
  uploading: { icon: Loader2, tone: "text-lavender", label: "Uploading" },
  processing: { icon: Loader2, tone: "text-orchid-glow", label: "Reading tags" },
  added: { icon: CheckCircle2, tone: "text-lavender", label: "Added" },
  duplicate: { icon: Copy, tone: "text-orchid-glow", label: "Duplicate" },
  rejected: { icon: Ban, tone: "text-subtle", label: "Skipped" },
  failed: { icon: AlertTriangle, tone: "text-rose", label: "Failed" },
};

function QueueRow({ item, onRetry }: { item: QueueItem; onRetry: () => void }) {
  const look = QUEUE_LOOK[item.status];
  const Icon = look.icon;
  const busy = item.status === "queued" || item.status === "uploading" || item.status === "processing";
  const title = item.upload?.song?.title;
  return (
    <li className="flex items-center gap-3 px-4 py-3">
      <span className={cn("grid size-9 shrink-0 place-items-center rounded-full bg-deep-purple/60 ring-1 ring-lavender/10", look.tone)}>
        <Icon className={cn("size-4", busy && "animate-spin")} />
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-3">
          <p className="min-w-0 truncate text-sm font-bold text-heading" title={item.file.name}>
            {title ?? item.file.name}
          </p>
          <span className={cn("shrink-0 text-xs font-bold", look.tone)}>
            {item.status === "uploading" ? `${Math.round(item.progress * 100)}%` : look.label}
          </span>
        </div>
        {busy ? (
          <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-deep-purple" role="progressbar" aria-valuenow={Math.round(item.progress * 100)} aria-valuemin={0} aria-valuemax={100} aria-label={`Uploading ${item.file.name}`}>
            <div
              className={cn(
                "h-full rounded-full bg-gradient-to-r from-violet via-wisteria to-lavender transition-[width] duration-200",
                item.status === "processing" && "animate-pulse",
              )}
              style={{ width: `${Math.max(item.status === "queued" ? 0 : 3, item.progress * 100)}%` }}
            />
          </div>
        ) : (
          <p className="mt-0.5 truncate text-xs text-muted-foreground">
            {title && <span className="text-subtle">{item.file.name} · </span>}
            {item.message}
          </p>
        )}
        {busy && <p className="mt-1 text-xs text-subtle">{formatBytes(item.file.size)}</p>}
      </div>
      {item.status === "failed" && (
        <Button size="sm" variant="outline" onClick={onRetry}>
          <RotateCw data-icon="inline-start" /> Retry
        </Button>
      )}
    </li>
  );
}

function UploadQueue({ items, onRetry, onClear }: { items: QueueItem[]; onRetry: (key: string) => void; onClear: () => void }) {
  const count = (s: QueueItem["status"]) => items.filter((i) => i.status === s).length;
  const running = count("queued") + count("uploading") + count("processing");
  const summary = [
    running && `${running} in progress`,
    count("added") && `${count("added")} added`,
    count("duplicate") && plural(count("duplicate"), "duplicate"),
    count("rejected") && `${count("rejected")} skipped`,
    count("failed") && `${count("failed")} failed`,
  ].filter(Boolean);
  return (
    <section className="glass glass-inset mt-6 overflow-hidden rounded-[1.75rem]" aria-label="Uploads">
      <header className="flex items-center justify-between gap-3 border-b border-border px-4 py-3">
        <div>
          <h2 className="font-display text-xl font-semibold text-heading">Uploads</h2>
          <p className="text-xs text-muted-foreground" aria-live="polite">{summary.join(" · ")}</p>
        </div>
        {running < items.length && (
          <Button size="sm" variant="ghost" onClick={onClear} className="text-muted-foreground">
            Clear finished
          </Button>
        )}
      </header>
      <ul className="max-h-[22rem] divide-y divide-border overflow-y-auto">
        {items.map((item) => (
          <QueueRow key={item.key} item={item} onRetry={() => onRetry(item.key)} />
        ))}
      </ul>
    </section>
  );
}

function AnalysisBadge({ upload }: { upload: LibraryUpload }) {
  const f = upload.features;
  let badge: React.ReactNode;
  let tip: string;
  switch (upload.analysis_status) {
    case "pending":
    case "running":
      badge = (
        <Badge variant="highlight" className="gap-1" aria-label="Analysing">
          <Loader2 className="size-3 animate-spin" /> <span className="hidden sm:inline">Analysing</span>
        </Badge>
      );
      tip = "Measuring tempo, energy and key in the background.";
      break;
    case "done": {
      const parts = [f?.tempo ? `${Math.round(f.tempo)} BPM` : null, f?.key_name].filter(Boolean);
      badge = (
        <Badge variant="genre" className="gap-1">
          <AudioLines className="size-3" />
          <span className="sm:hidden">{parts[0]?.replace(/ (major|minor)$/, (m) => (m === " minor" ? "m" : "")) ?? "Analysed"}</span>
          <span className="hidden sm:inline">{parts.length ? parts.join(" · ") : "Analysed"}</span>
        </Badge>
      );
      tip = [
        f?.energy != null && `Energy ${Math.round(f.energy * 100)}%`,
        f?.spectral_centroid_hz != null && `brightness ${Math.round(f.spectral_centroid_hz)} Hz`,
        !f?.tempo && "no steady beat found",
        f?.analyzer && `measured with ${f.analyzer}`,
      ].filter(Boolean).join(" · ");
      break;
    }
    case "failed":
      badge = (
        <Badge variant="outline" className="gap-1 border-rose/40 text-rose" aria-label="Analysis failed">
          <AlertTriangle className="size-3" /> <span className="hidden sm:inline">Analysis failed</span>
        </Badge>
      );
      tip = upload.analysis_error ?? "The audio couldn't be analysed. It still plays normally.";
      break;
    default:
      badge = (
        <Badge variant="outline" className="text-subtle">
          <span className="sm:hidden">—</span>
          <span className="hidden sm:inline">Not analysed</span>
        </Badge>
      );
      tip = upload.analysis_error ?? "Audio analysis isn't available on this server.";
  }
  return (
    <Tooltip>
      <TooltipTrigger render={<span className="inline-flex shrink-0" />}>{badge}</TooltipTrigger>
      <TooltipContent>{tip}</TooltipContent>
    </Tooltip>
  );
}

function StorageNote({ limits }: { limits: LibraryLimits }) {
  return (
    <ul className="mt-4 flex flex-wrap gap-x-5 gap-y-1.5 text-xs text-subtle">
      <li className="flex items-center gap-1.5">
        <ShieldCheck className="size-3.5 text-lilac" /> Private: only you can see and play your files
      </li>
      <li className="flex items-center gap-1.5">
        <HardDrive className="size-3.5 text-lilac" />
        {limits.storage_backend === "r2" ? "Stored in Cloudflare R2" : "Stored on this server"}
      </li>
      <li className="flex items-center gap-1.5">
        <Sparkles className="size-3.5 text-lilac" />
        {limits.analysis_available ? "Tempo, energy and key measured after upload" : "Audio analysis is switched off"}
      </li>
    </ul>
  );
}

export function LibraryPage() {
  const library = useLibrary();
  const queue = useUploadQueue(library.data?.limits);
  const remove = useDeleteUpload();
  const player = usePlayer();
  const [confirming, setConfirming] = useState<LibraryUpload | null>(null);

  const uploads = (library.data?.items ?? []).filter((u): u is LibraryUpload & { song: Song } => u.song !== null);
  const songs = uploads.map((u) => u.song);
  const totalBytes = uploads.reduce((sum, u) => sum + u.size_bytes, 0);

  return (
    <div>
      <PageHeader
        eyebrow="your own files"
        title="My Library"
        description={
          uploads.length
            ? `${plural(uploads.length, "file")} · ${formatBytes(totalBytes)}. They play here and show up in your collection.`
            : "Upload music files you own. Tunewise reads their tags and cover art, and plays them right here."
        }
        actions={
          songs.length > 0 && (
            <Button variant="cta" onClick={() => player.play(songs[0], songs)}>
              <Play data-icon="inline-start" className="fill-current" /> Play all
            </Button>
          )
        }
      />

      <Dropzone onFiles={queue.add} accept={queue.accept} limits={library.data?.limits} compact={uploads.length > 0} />
      {library.data && <StorageNote limits={library.data.limits} />}

      {queue.items.length > 0 && <UploadQueue items={queue.items} onRetry={queue.retry} onClear={queue.clearFinished} />}

      <section className="mt-8">
        {library.isPending ? (
          <SongListSkeleton rows={4} />
        ) : library.isError ? (
          <ErrorState error={library.error} onRetry={() => library.refetch()} />
        ) : uploads.length === 0 ? (
          queue.items.length === 0 && (
            <EmptyState
              icon={FolderHeart}
              tone="orchid"
              title="Your library is empty"
              description="Bring the albums you bought, your own recordings or that rare B-side. Duplicates are skipped automatically, and nothing you upload is shared."
            />
          )
        ) : (
          <>
            <h2 className="mb-3 font-display text-2xl font-semibold text-heading">In your library</h2>
            <div className="glass glass-inset divide-y divide-white/10 overflow-hidden rounded-[1.75rem]">
              {uploads.map((u, i) => (
                <SongRow
                  key={u.id}
                  song={u.song}
                  queue={songs}
                  index={i}
                  meta={`${u.audio_format.toUpperCase()} · ${formatBytes(u.size_bytes)}`}
                  badges={<AnalysisBadge upload={u} />}
                  linkFacets
                  action={{
                    kind: "remove",
                    pending: remove.isPending && remove.variables?.id === u.id,
                    onRemove: () => setConfirming(u),
                    label: `Delete ${u.song.title} from My Library`,
                  }}
                />
              ))}
            </div>
          </>
        )}
      </section>

      <AlertDialog open={confirming !== null} onOpenChange={(open) => !open && setConfirming(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="font-display text-2xl">Delete this file?</AlertDialogTitle>
            <AlertDialogDescription>
              “{confirming?.song?.title}” ({confirming?.original_filename}) will be removed from My Library and your
              collection, and the stored file is deleted. You can upload it again later.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep it</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              onClick={() => {
                if (confirming) {
                  if (player.current?.id === confirming.song?.id) player.stop();
                  remove.mutate(confirming);
                }
                setConfirming(null);
              }}
            >
              Delete file
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
