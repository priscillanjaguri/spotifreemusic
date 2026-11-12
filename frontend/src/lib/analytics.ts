import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { api } from "./api";
import type { AnalyticsPeriod } from "./types";

export function useAnalytics(period: AnalyticsPeriod, offset = 0) {
  return useQuery({
    queryKey: ["analytics", period, offset],
    queryFn: () => api.analytics(period, offset),
  });
}

export function useTasteTimeline(weeks = 12) {
  return useQuery({
    queryKey: ["taste-timeline", weeks],
    queryFn: () => api.tasteTimeline(weeks),
  });
}

export function useMemoryLane(limit = 24) {
  return useQuery({
    queryKey: ["memory-lane", limit],
    queryFn: () => api.memoryLane(limit),
  });
}

export function usePreferences() {
  return useQuery({
    queryKey: ["preferences"],
    queryFn: () => api.preferences(),
  });
}

export function useUpdatePreferences() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: Parameters<typeof api.updatePreferences>[0]) => api.updatePreferences(body),
    onSuccess: (data) => {
      qc.setQueryData(["preferences"], data);
      void qc.invalidateQueries({ queryKey: ["analytics"] });
      void qc.invalidateQueries({ queryKey: ["taste-timeline"] });
      void qc.invalidateQueries({ queryKey: ["memory-lane"] });
      void qc.invalidateQueries({ queryKey: ["companion"] });
      void qc.invalidateQueries({ queryKey: ["for-you"] });
    },
  });
}

export function useDeleteListeningHistory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.deleteListeningHistory(),
    onSuccess: (data) => {
      void qc.invalidateQueries({ queryKey: ["analytics"] });
      void qc.invalidateQueries({ queryKey: ["taste-timeline"] });
      void qc.invalidateQueries({ queryKey: ["memory-lane"] });
      void qc.invalidateQueries({ queryKey: ["companion"] });
      void qc.invalidateQueries({ queryKey: ["for-you"] });
      toast.success(
        data.deleted_events === 0
          ? "Listening history was already empty."
          : `Deleted ${data.deleted_events} listening event${data.deleted_events === 1 ? "" : "s"}.`,
      );
    },
    onError: (err: Error) => toast.error(err.message || "Couldn't delete listening history."),
  });
}
