import type {
  CollectionFacets,
  CollectionFilter,
  CollectionItem,
  CollectionPage,
  CollectionSource,
  SongSearchResponse,
  User,
} from "./types";

const BASE = "/api/v1";

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

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE}${path}`, {
      credentials: "include",
      ...init,
      headers: { ...(init.body ? { "Content-Type": "application/json" } : {}), ...init.headers },
    });
  } catch {
    throw new ApiError(0, "Can't reach Tunewise right now. Check your connection and try again.");
  }

  if (response.status === 204) return undefined as T;

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const fallback =
      response.status >= 500
        ? "Something went wrong on our side. Please try again in a moment."
        : `Request failed (${response.status})`;
    const { message, code } = messageFromDetail(body?.detail, fallback);
    throw new ApiError(response.status, message, code);
  }
  return body as T;
}

const json = (data: unknown) => JSON.stringify(data);

export const api = {
  me: () => request<User>("/auth/me"),
  login: (email: string, password: string) =>
    request<User>("/auth/login", { method: "POST", body: json({ email, password }) }),
  register: (email: string, password: string, display_name: string) =>
    request<User>("/auth/register", { method: "POST", body: json({ email, password, display_name }) }),
  logout: () => request<void>("/auth/logout", { method: "POST" }),

  searchSongs: (q: string, limit = 24) =>
    request<SongSearchResponse>(`/songs/search?${new URLSearchParams({ q, limit: String(limit) })}`),

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
};
