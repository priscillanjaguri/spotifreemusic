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
  source_label?: string | null;
  k: number;
};

export type OnlineSeriesPoint = {
  date: string;
  labeled: number;
  engage_rate: number;
  skip_rate: number;
  like_rate: number;
  play_rate: number;
};

export type OnlineMetrics = {
  ready: boolean;
  min_labeled_required: number;
  metrics: Record<string, number>;
  label_sources: Record<string, number>;
  series: OnlineSeriesPoint[];
  metric_blurbs: Record<string, string>;
};

export type HoldoutReady = {
  ready: boolean;
  min_positives: number;
  catalogue_songs: number;
  qualifying_users: number;
  preferred_source: "holdout" | "synthetic";
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
  online?: OnlineMetrics | null;
  holdout?: HoldoutReady | null;
  source_labels?: Record<string, string>;
};

export type EvalStatus = {
  latest_id: number | null;
  latest_source: "holdout" | "synthetic" | null;
  latest_source_label: string | null;
  holdout: HoldoutReady;
  online: {
    ready: boolean;
    min_labeled_required: number;
    metrics: Record<string, number>;
    label_sources: Record<string, number>;
  };
  schedule: EvalSummary["schedule"];
  run_secret_configured: boolean;
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

export function fetchEvalStatus() {
  return evalRequest<EvalStatus>("/eval/status");
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

export function useEvalStatus() {
  return useQuery({ queryKey: ["eval", "status"], queryFn: fetchEvalStatus, staleTime: 30_000 });
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

/** Offline hold-out ranking metrics (precision/recall/…). */
export const OFFLINE_METRIC_ORDER = ["precision_at_k", "recall_at_k", "diversity", "coverage"] as const;

/** Live impression outcome rates. */
export const ONLINE_METRIC_ORDER = ["engage_rate", "skip_rate", "like_rate", "play_rate"] as const;

/** @deprecated Prefer OFFLINE_METRIC_ORDER — kept for older imports. */
export const METRIC_ORDER = OFFLINE_METRIC_ORDER;

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
    case "engage_rate":
      return "Engage rate";
    case "skip_rate":
      return "Skip rate";
    case "like_rate":
      return "Like rate";
    case "play_rate":
      return "Play rate";
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
