/** Runtime API origin for Capacitor / cross-origin clients. Empty = same-origin `/api`. */

const STORAGE_KEY = "tunewise_api_base";
const TOKEN_KEY = "tunewise_access_token";

function fromEnv(): string {
  const raw = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() ?? "";
  return normalizeApiBase(raw);
}

/** Strip trailing slash; reject path-only values. */
export function normalizeApiBase(raw: string): string {
  const trimmed = raw.trim().replace(/\/+$/, "");
  if (!trimmed) return "";
  try {
    const u = new URL(trimmed);
    if (u.protocol !== "http:" && u.protocol !== "https:") return "";
    return `${u.protocol}//${u.host}`;
  } catch {
    return "";
  }
}

export function getApiBase(): string {
  if (typeof localStorage !== "undefined") {
    const stored = normalizeApiBase(localStorage.getItem(STORAGE_KEY) ?? "");
    if (stored) return stored;
  }
  return fromEnv();
}

export function setApiBase(raw: string): string {
  const next = normalizeApiBase(raw);
  if (typeof localStorage !== "undefined") {
    if (next) localStorage.setItem(STORAGE_KEY, next);
    else localStorage.removeItem(STORAGE_KEY);
  }
  return next;
}

/** Origin used for API calls; empty string means relative `/api/v1`. */
export function apiOrigin(): string {
  return getApiBase();
}

export function apiV1Base(): string {
  const origin = apiOrigin();
  return origin ? `${origin}/api/v1` : "/api/v1";
}

export function getAccessToken(): string | null {
  if (typeof localStorage === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setAccessToken(token: string | null): void {
  if (typeof localStorage === "undefined") return;
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

/**
 * Turn a relative API media path into an absolute URL the WebView can load.
 * Appends access_token for authenticated library streams/covers when needed.
 */
export function resolveMediaUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  let absolute = url;
  if (url.startsWith("/")) {
    const origin = apiOrigin();
    absolute = origin ? `${origin}${url}` : url;
  }
  const token = getAccessToken();
  if (!token) return absolute;
  // Only attach token to our own API paths (library stream/cover, mock audio).
  try {
    const parsed = new URL(absolute, typeof window !== "undefined" ? window.location.origin : "http://localhost");
    const isOurApi =
      parsed.pathname.startsWith("/api/v1/library/") || parsed.pathname.startsWith("/api/v1/dev/");
    if (!isOurApi) return absolute;
    if (parsed.searchParams.has("access_token")) return absolute;
    parsed.searchParams.set("access_token", token);
    return parsed.toString();
  } catch {
    return absolute;
  }
}

export async function probeApiBase(base: string): Promise<{ ok: boolean; message: string }> {
  const origin = normalizeApiBase(base);
  if (!origin) return { ok: false, message: "Enter a full URL like http://192.168.1.20:8741" };
  try {
    const res = await fetch(`${origin}/api/v1/health`, { method: "GET" });
    if (!res.ok) return { ok: false, message: `Server responded with ${res.status}` };
    const body = (await res.json().catch(() => null)) as { status?: string } | null;
    if (body?.status !== "ok") return { ok: false, message: "Unexpected health response" };
    return { ok: true, message: "Connected" };
  } catch {
    return {
      ok: false,
      message: "Can't reach that host. Use the PC's LAN IP (same Wi‑Fi) or a public HTTPS URL.",
    };
  }
}
