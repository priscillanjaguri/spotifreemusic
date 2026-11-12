import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { ApiError, api, uploadToLibrary } from "./api";
import { collectionKeys } from "./collection";
import type { LibraryPage, LibraryUpload } from "./types";

export const libraryKeys = { all: ["library"] as const };

const ACCEPT_FALLBACK = [".aac", ".flac", ".m4a", ".mp3", ".oga", ".ogg", ".wav"];
const CONCURRENCY = 2;

const analysing = (u: LibraryUpload) => u.analysis_status === "pending" || u.analysis_status === "running";

export function useLibrary() {
  return useQuery({
    queryKey: libraryKeys.all,
    queryFn: api.library,
    // Analysis runs in the background after upload; poll until every file has a result.
    refetchInterval: (query) => ((query.state.data as LibraryPage | undefined)?.items.some(analysing) ? 2500 : false),
  });
}

export function useDeleteUpload() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (upload: LibraryUpload) => api.deleteUpload(upload.id),
    onMutate: async (upload) => {
      await queryClient.cancelQueries({ queryKey: libraryKeys.all });
      const previous = queryClient.getQueryData<LibraryPage>(libraryKeys.all);
      if (previous) {
        queryClient.setQueryData<LibraryPage>(libraryKeys.all, {
          ...previous,
          total: previous.total - 1,
          items: previous.items.filter((u) => u.id !== upload.id),
        });
      }
      return { previous };
    },
    onSuccess: (_d, upload) => toast.success(`Deleted “${upload.song?.title ?? upload.original_filename}” from your library`),
    onError: (err, _u, ctx) => {
      if (ctx?.previous) queryClient.setQueryData(libraryKeys.all, ctx.previous);
      toast.error(err instanceof ApiError ? err.message : "Couldn't delete that file.");
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: libraryKeys.all });
      queryClient.invalidateQueries({ queryKey: collectionKeys.all });
    },
  });
}

export type QueueStatus = "queued" | "uploading" | "processing" | "added" | "duplicate" | "rejected" | "failed";

export type QueueItem = {
  key: string;
  file: File;
  status: QueueStatus;
  progress: number;
  message?: string;
  upload?: LibraryUpload | null;
};

const extensionOf = (name: string) => {
  const dot = name.lastIndexOf(".");
  return dot >= 0 ? name.slice(dot).toLowerCase() : "";
};

/** Client-side queue: checks type and size up front, uploads two at a time, one request per file. */
export function useUploadQueue(limits?: { accepted_extensions: string[]; max_file_mb: number }) {
  const queryClient = useQueryClient();
  const [items, setItems] = useState<QueueItem[]>([]);
  const itemsRef = useRef(items);
  itemsRef.current = items;
  const active = useRef(0);
  const counter = useRef(0);
  const accepted = limits?.accepted_extensions ?? ACCEPT_FALLBACK;
  const maxBytes = (limits?.max_file_mb ?? 200) * 1024 * 1024;

  const patch = useCallback((key: string, change: Partial<QueueItem>) => {
    setItems((list) => list.map((i) => (i.key === key ? { ...i, ...change } : i)));
  }, []);

  const pump = useCallback(() => {
    while (active.current < CONCURRENCY) {
      const next = itemsRef.current.find((i) => i.status === "queued");
      if (!next) return;
      active.current += 1;
      itemsRef.current = itemsRef.current.map((i) => (i.key === next.key ? { ...i, status: "uploading" } : i));
      patch(next.key, { status: "uploading", progress: 0 });
      uploadToLibrary(next.file, (fraction) =>
        patch(next.key, fraction >= 1 ? { progress: 1, status: "processing" } : { progress: fraction }),
      )
        .then((result) => {
          patch(next.key, { status: result.status, progress: 1, message: result.message, upload: result.upload });
          queryClient.invalidateQueries({ queryKey: libraryKeys.all });
          queryClient.invalidateQueries({ queryKey: collectionKeys.all });
        })
        .catch((err: unknown) =>
          patch(next.key, { status: "failed", message: err instanceof ApiError ? err.message : "Upload failed." }),
        )
        .finally(() => {
          active.current -= 1;
          pump();
        });
    }
  }, [patch, queryClient]);

  useEffect(() => {
    if (items.some((i) => i.status === "queued")) pump();
  }, [items, pump]);

  const add = useCallback(
    (files: FileList | File[]) => {
      const fresh: QueueItem[] = Array.from(files).map((file) => {
        const key = `${++counter.current}-${file.name}`;
        const ext = extensionOf(file.name);
        const mimeOk = typeof file.type === "string" && file.type.startsWith("audio/");
        // Android Chrome sometimes omits the extension; accept by MIME too.
        if (ext && !accepted.includes(ext) && !mimeOk) {
          return { key, file, status: "rejected", progress: 0, message: "Not a supported audio file. Skipped." };
        }
        if (!ext && !mimeOk) {
          return { key, file, status: "rejected", progress: 0, message: "Not a supported audio file. Skipped." };
        }
        if (file.size > maxBytes) {
          return { key, file, status: "rejected", progress: 0, message: `Larger than ${limits?.max_file_mb ?? 200} MB. Skipped.` };
        }
        if (file.size === 0) return { key, file, status: "rejected", progress: 0, message: "Empty file. Skipped." };
        return { key, file, status: "queued", progress: 0 };
      });
      setItems((list) => [...fresh, ...list]);
    },
    [accepted, maxBytes, limits?.max_file_mb],
  );

  const retry = useCallback((key: string) => patch(key, { status: "queued", progress: 0, message: undefined }), [patch]);
  const clearFinished = useCallback(
    () => setItems((list) => list.filter((i) => ["queued", "uploading", "processing"].includes(i.status))),
    [],
  );

  // Broad accept list helps Android Chrome's file picker surface audio files.
  const acceptAttr = [
    "audio/*",
    "audio/mpeg",
    "audio/mp4",
    "audio/x-m4a",
    "audio/aac",
    "audio/flac",
    "audio/ogg",
    "audio/wav",
    "audio/x-wav",
    ...accepted,
  ].join(",");

  return { items, add, retry, clearFinished, accept: acceptAttr };
}
