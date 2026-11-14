import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiV1Base } from "./config";
import { ApiError } from "./api";

export type EvalSnapshot = {
  id: number;
  created_at: string | null;
  metrics: Record<string, number>;
  data_volume: Record<string, number>;
  feedback_counts: Record<string, number>;
  source: "holdout" | "synthetic";
  k: number;
};

export type EvalSummary = {
  latest: EvalSnapshot | null;
  metric_blurbs: Record<string, string>;
  ranking_blurb: string;
  schedule: {
    due: boolean;
    reason: string | null;
    new_events_since_last: number;
    hours_since_last: number | null;
    threshold_events?: number | null;
    daily_hours?: number | null;
  };
};

export type EvalSnapshotsResponse = {
  items: EvalSnapshot[];
  total: number;
};

async function evalRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiV1Base()}${path}`, {
      credentials: "include",
      ...init,
      headers: {
        ...(init.body ? { "Content-Type": "application/json" } : {}),
        ...(init.headers as Record<string, string> | undefined),
      },
    });
  } catch {
    throw new ApiError(0, "Can't reach Spotifree right now. Try again in a moment.");
  }
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body?.detail;
    const message =
      typeof detail === "string"
        ? detail
        : detail?.message || (response.status === 401 ? "Invalid eval secret" : `Request failed (${response.status})`);
    throw new ApiError(response.status, message, detail?.code ?? null);
  }
  return body as T;
}

export function fetchEvalSummary() {
  return evalRequest<EvalSummary>("/eval/summary");
}

export function fetchEvalSnapshots(limit = 30) {
  return evalRequest<EvalSnapshotsResponse>(`/eval/snapshots?${new URLSearchParams({ limit: String(limit) })}`);
}

export function runEval(secret: string, opts?: { k?: number; force_synthetic?: boolean }) {
  return evalRequest<{ snapshot: EvalSnapshot; message: string }>("/eval/run", {
    method: "POST",
    headers: { "X-Eval-Secret": secret },
    body: JSON.stringify({
      k: opts?.k ?? 10,
      force_synthetic: opts?.force_synthetic ?? false,
    }),
  });
}

export function useEvalSummary() {
  return useQuery({ queryKey: ["eval", "summary"], queryFn: fetchEvalSummary, staleTime: 30_000 });
}

export function useEvalSnapshots() {
  return useQuery({ queryKey: ["eval", "snapshots"], queryFn: () => fetchEvalSnapshots(40), staleTime: 30_000 });
}

export function useRunEval() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ secret, forceSynthetic }: { secret: string; forceSynthetic?: boolean }) =>
      runEval(secret, { force_synthetic: forceSynthetic }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["eval"] });
    },
  });
}

export const METRIC_ORDER = ["precision_at_k", "recall_at_k", "diversity", "coverage"] as const;

export function metricLabel(key: string): string {
  switch (key) {
    case "precision_at_k":
      return "Precision@k";
    case "recall_at_k":
      return "Recall@k";
    case "diversity":
      return "Diversity";
    case "coverage":
      return "Coverage";
    default:
      return key.replace(/_/g, " ");
  }
}

export function formatMetric(value: number | undefined): string {
  if (value == null || Number.isNaN(value)) return "—";
  return (value * 100).toFixed(1) + "%";
}

export function formatWhen(iso: string | null | undefined): string {
  if (!iso) return "Never";
  const d = new Date(iso);
  return d.toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}
