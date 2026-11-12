import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./api";
import type { CompanionMood } from "./types";

export function useDailyCompanion(mood: string | null, limit = 12) {
  return useQuery({
    queryKey: ["companion", "daily", mood, limit],
    queryFn: () => api.dailyCompanion(mood, limit),
  });
}

export function useSetCompanionMood() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (mood: CompanionMood) => api.setCompanionMood(mood),
    onSuccess: (data) => {
      qc.setQueryData(["companion", "daily", data.mood, 12], data);
      void qc.invalidateQueries({ queryKey: ["companion"] });
    },
  });
}
