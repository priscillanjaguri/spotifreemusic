import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ApiError, api } from "./api";
import type { CollectionFilter, CollectionSource, Song } from "./types";

const PAGE_SIZE = 50;
// The collection endpoint caps a page at 100, so "is this saved?" is answered from the newest 100 songs
// plus whatever this session has added. A 409 on add still tells us the truth for older songs.
const SAVED_WINDOW = 100;

export const collectionKeys = {
  all: ["collection"] as const,
  list: (filter: CollectionFilter | null) => ["collection", "list", filter] as const,
  facets: ["collection", "facets"] as const,
  saved: ["collection", "saved"] as const,
  recent: ["collection", "recent"] as const,
};

export function useCollection(filter: CollectionFilter | null) {
  return useInfiniteQuery({
    queryKey: collectionKeys.list(filter),
    queryFn: ({ pageParam }) => api.collection(filter, PAGE_SIZE, pageParam),
    initialPageParam: 0,
    getNextPageParam: (last) => (last.offset + last.items.length < last.total ? last.offset + last.items.length : undefined),
  });
}

export function useRecentlyAdded(limit = 6) {
  return useQuery({ queryKey: [...collectionKeys.recent, limit], queryFn: () => api.collection(null, limit, 0) });
}

export function useFacets() {
  return useQuery({ queryKey: collectionKeys.facets, queryFn: api.facets });
}

export function useSavedSongIds() {
  return useQuery({
    queryKey: collectionKeys.saved,
    queryFn: async () => new Set((await api.collection(null, SAVED_WINDOW, 0)).items.map((i) => i.song.id)),
  });
}

function setSaved(queryClient: ReturnType<typeof useQueryClient>, songId: number, saved: boolean) {
  queryClient.setQueryData<Set<number>>(collectionKeys.saved, (prev) => {
    const next = new Set(prev);
    if (saved) next.add(songId);
    else next.delete(songId);
    return next;
  });
}

export function useAddToCollection(source: CollectionSource = "search") {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (song: Song) => api.addToCollection(song.id, source),
    onSuccess: (_data, song) => {
      setSaved(queryClient, song.id, true);
      toast.success(`Added “${song.title}” to your collection`);
    },
    onError: (err, song) => {
      if (err instanceof ApiError && err.status === 409) {
        setSaved(queryClient, song.id, true);
        toast.info(`“${song.title}” is already in your collection`);
        return;
      }
      toast.error(err instanceof ApiError ? err.message : "Couldn't add that song. Try again.");
    },
    onSettled: () => queryClient.invalidateQueries({ queryKey: collectionKeys.all }),
  });
}

export function useRemoveFromCollection() {
  const queryClient = useQueryClient();
  const add = useAddToCollection("manual");
  return useMutation({
    mutationFn: (song: Song) => api.removeFromCollection(song.id),
    onSuccess: (_data, song) => {
      setSaved(queryClient, song.id, false);
      toast(`Removed “${song.title}”`, {
        action: { label: "Undo", onClick: () => add.mutate(song) },
      });
    },
    onError: (err) => toast.error(err instanceof ApiError ? err.message : "Couldn't remove that song. Try again."),
    onSettled: () => queryClient.invalidateQueries({ queryKey: collectionKeys.all }),
  });
}
