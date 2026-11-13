import type {
  AnalyticsPeriod,
  AnalyticsResponse,
  CollectionFacets,
  CollectionFilter,
  CollectionItem,
  CollectionPage,
  CollectionSource,
  CompanionMood,
  DailyCompanion,
  FeedbackAction,
  LibraryPage,
  LibraryUpload,
  ListeningEventPayload,
  Lyrics,
  MemoryLane,
  Preferences,
  RecommendationsResponse,
  SongSearchResponse,
  TasteTimeline,
  UploadResult,
  User,
} from "./types";
import { apiV1Base, getAccessToken, setAccessToken } from "./config";

/** A failed API call. `code` is set when the backend sends a structured `{code, message}` detail. */
export class ApiError extends Error {
  readonly status: number;
  readonly code: string | null;

  constructor(status: number, message: string, code: string | null = null) {
    super(message);
    this.status = status;
    this.code = code;
  }

  get isProviderNotConfigured() {
    return this.status === 503 && this.code === "provider_not_configured";
  }
}

type ValidationIssue = { loc?: (string | number)[]; msg?: string };

const FIELD_LABELS: Record<string, string> = {
  email: "Email",
  password: "Password",
  display_name: "Name",
  q: "Search",
};

function messageFromDetail(detail: unknown, fallback: string): { message: string; code: string | null } {
  if (typeof detail === "string") return { message: detail, code: null };
  if (Array.isArray(detail)) {
    const issue = detail[0] as ValidationIssue | undefined;
    if (issue?.msg) {
      const field = String(issue.loc?.[issue.loc.length - 1] ?? "");
      const label = FIELD_LABELS[field];
      const msg = issue.msg.replace(/^Value error, /, "");
      return { message: label ? `${label}: ${msg.charAt(0).toLowerCase()}${msg.slice(1)}` : msg, code: null };
    }
  }
  if (detail && typeof detail === "object" && "message" in detail) {
    const d = detail as { message: string; code?: string };
    return { message: d.message, code: d.code ?? null };
  }
  return { message: fallback, code: null };
}

function apiErrorFrom(status: number, body: { detail?: unknown } | null): ApiError {
  const fallback =
    status >= 500 ? "Something went wrong on our side. Please try again in a moment." : `Request failed (${status})`;
  const { message, code } = messageFromDetail(body?.detail, fallback);
  return new ApiError(status, message, code);
}

function authHeaders(): Record<string, string> {
  const token = getAccessToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

function rememberSession(user: User): User {
  if (user.access_token) setAccessToken(user.access_token);
  const { access_token: _drop, ...rest } = user;
  return rest as User;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  const headers: Record<string, string> = {
    ...(init.body ? { "Content-Type": "application/json" } : {}),
    ...authHeaders(),
    ...(init.headers as Record<string, string> | undefined),
  };
  try {
    response = await fetch(`${apiV1Base()}${path}`, {
      credentials: "include",
      ...init,
      headers,
    });
  } catch {
    throw new ApiError(0, "Can't reach Spotifree right now. Check your Server URL and try again.");
  }

  if (response.status === 204) return undefined as T;

  const body = await response.json().catch(() => null);
  if (!response.ok) throw apiErrorFrom(response.status, body);
  return body as T;
}

/**
 * Upload one file with progress events (fetch can't report upload progress, XMLHttpRequest can).
 * The endpoint accepts many files per request; the UI sends one per request so each gets its own bar.
 */
export function uploadToLibrary(
  file: File,
  onProgress: (fraction: number) => void,
  signal?: AbortSignal,
): Promise<UploadResult> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${apiV1Base()}/library/uploads`);
    xhr.withCredentials = true;
    const token = getAccessToken();
    if (token) xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    xhr.responseType = "json";
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(e.loaded / e.total);
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        const result = (xhr.response as { results?: UploadResult[] } | null)?.results?.[0];
        if (result) resolve(result);
        else reject(new ApiError(xhr.status, "The server sent an unexpected response."));
      } else {
        reject(
          xhr.status === 413
            ? new ApiError(413, "This file is too large for the server to accept.")
            : apiErrorFrom(xhr.status, xhr.response),
        );
      }
    };
    xhr.onerror = () => reject(new ApiError(0, "Upload interrupted. Check your connection and try again."));
    xhr.onabort = () => reject(new ApiError(0, "Upload cancelled."));
    signal?.addEventListener("abort", () => xhr.abort());
    const form = new FormData();
    form.append("files", file, file.name);
    xhr.send(form);
  });
}

const json = (data: unknown) => JSON.stringify(data);

export const api = {
  me: () => request<User>("/auth/me"),
  login: async (email: string, password: string) =>
    rememberSession(await request<User>("/auth/login", { method: "POST", body: json({ email, password }) })),
  register: async (email: string, password: string, display_name: string) =>
    rememberSession(
      await request<User>("/auth/register", { method: "POST", body: json({ email, password, display_name }) }),
    ),
  logout: async () => {
    try {
      await request<void>("/auth/logout", { method: "POST" });
    } finally {
      setAccessToken(null);
    }
  },

  searchSongs: (q: string, limit = 24) =>
    request<SongSearchResponse>(`/songs/search?${new URLSearchParams({ q, limit: String(limit) })}`),

  lyrics: (songId: number) => request<Lyrics>(`/lyrics/${songId}`),

  collection: (filter: CollectionFilter | null, limit = 50, offset = 0) => {
    const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (filter?.artistId) params.set("artist_id", String(filter.artistId));
    if (filter?.albumId) params.set("album_id", String(filter.albumId));
    if (filter?.genre) params.set("genre", filter.genre);
    return request<CollectionPage>(`/collection?${params}`);
  },
  facets: () => request<CollectionFacets>("/collection/facets"),
  addToCollection: (song_id: number, source: CollectionSource = "search") =>
    request<CollectionItem>("/collection", { method: "POST", body: json({ song_id, source }) }),
  removeFromCollection: (song_id: number) => request<void>(`/collection/${song_id}`, { method: "DELETE" }),

  library: () => request<LibraryPage>("/library"),
  libraryItem: (id: number) => request<LibraryUpload>(`/library/${id}`),
  deleteUpload: (id: number) => request<void>(`/library/${id}`, { method: "DELETE" }),

  recommendations: (limit = 24) =>
    request<RecommendationsResponse>(`/recommendations?${new URLSearchParams({ limit: String(limit) })}`),
  similarSongs: (songId: number, limit = 12) =>
    request<RecommendationsResponse>(
      `/songs/${songId}/similar?${new URLSearchParams({ limit: String(limit) })}`,
    ),
  feedback: (song_id: number, action: FeedbackAction, context = "recommendations") =>
    request<{ song_id: number; interaction_type: string; created_at: string }>("/feedback", {
      method: "POST",
      body: json({ song_id, action, context }),
    }),
  listeningEvent: (payload: ListeningEventPayload) =>
    request<{ id: number; song_id: number; listened_ms: number; completed: boolean | null; play_date: string } | null>(
      "/listening/events",
      { method: "POST", body: json(payload) },
    ),
  deleteListeningHistory: () =>
    request<{ deleted_events: number; deleted_sessions: number }>("/listening/history", { method: "DELETE" }),

  analytics: (period: AnalyticsPeriod = "week", offset = 0) =>
    request<AnalyticsResponse>(
      `/analytics?${new URLSearchParams({ period, offset: String(offset) })}`,
    ),
  tasteTimeline: (weeks = 12) =>
    request<TasteTimeline>(`/analytics/taste-timeline?${new URLSearchParams({ weeks: String(weeks) })}`),
  memoryLane: (limit = 24) =>
    request<MemoryLane>(`/analytics/memory-lane?${new URLSearchParams({ limit: String(limit) })}`),

  dailyCompanion: (mood?: string | null, limit = 12) => {
    const params = new URLSearchParams({ limit: String(limit) });
    if (mood) params.set("mood", mood);
    return request<DailyCompanion>(`/companion/daily?${params}`);
  },
  setCompanionMood: (mood: CompanionMood, limit = 12) =>
    request<DailyCompanion>(`/companion/daily?${new URLSearchParams({ limit: String(limit) })}`, {
      method: "POST",
      body: json({ mood }),
    }),

  preferences: () => request<Preferences>("/profile/preferences"),
  updatePreferences: (body: Partial<Preferences> & { preferred_genres?: string[] }) =>
    request<Preferences>("/profile/preferences", { method: "PATCH", body: json(body) }),
};
