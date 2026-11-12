import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { ApiError, api } from "./api";
import type { FeedbackAction, Song } from "./types";

export const recoKeys = {
  all: ["recommendations"] as const,
  forYou: (limit: number) => ["recommendations", "for-you", limit] as const,
  similar: (songId: number) => ["recommendations", "similar", songId] as const,
};

export function useForYou(limit = 24) {
  return useQuery({ queryKey: recoKeys.forYou(limit), queryFn: () => api.recommendations(limit) });
}

export function useSimilar(songId: number | null, limit = 12) {
  return useQuery({
    queryKey: recoKeys.similar(songId ?? 0),
    queryFn: () => api.similarSongs(songId!, limit),
    enabled: songId != null && songId > 0,
  });
}

export function useFeedback(context = "recommendations") {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ song, action }: { song: Song; action: FeedbackAction }) =>
      api.feedback(song.id, action, context),
    onSuccess: (_data, { song, action }) => {
      toast.success(action === "like" ? `Liked “${song.title}”` : `We'll skip “${song.title}”`);
      void queryClient.invalidateQueries({ queryKey: recoKeys.all });
    },
    onError: (err) => toast.error(err instanceof ApiError ? err.message : "Couldn't save that feedback."),
  });
}

export function useSeedGenres() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (preferred_genres: string[]) => api.updatePreferences({ preferred_genres }),
    onSuccess: () => {
      toast.success("Taste seeds saved — refreshing picks");
      void queryClient.invalidateQueries({ queryKey: recoKeys.all });
    },
    onError: (err) => toast.error(err instanceof ApiError ? err.message : "Couldn't save genres."),
  });
}
