/**
 * Offline My Library cache for Capacitor.
 *
 * Metadata → Preferences JSON. Audio → Filesystem (Directory.Data).
 * Online: refresh metadata + download missing streams. Offline: serve cache only.
 */
import { Capacitor } from "@capacitor/core";
import { Directory, Filesystem } from "@capacitor/filesystem";
import { Preferences } from "@capacitor/preferences";
import { getAccessToken, resolveMediaUrl } from "./config";
import type { LibraryPage, LibraryUpload, Song } from "./types";

const META_KEY = "spotifree_library_cache_v1";
const USER_KEY = "spotifree_offline_user_v1";
const AUDIO_DIR = "library-audio";

type CachedLibrary = {
  savedAt: string;
  page: LibraryPage;
};

function nativeOk(): boolean {
  return Capacitor.isNativePlatform();
}

function audioPath(uploadId: number): string {
  return `${AUDIO_DIR}/${uploadId}.bin`;
}

export async function saveOfflineUser(user: { id: string; email: string; display_name: string; created_at: string }): Promise<void> {
  if (!nativeOk()) return;
  await Preferences.set({ key: USER_KEY, value: JSON.stringify(user) });
}

export async function loadOfflineUser(): Promise<{
  id: string;
  email: string;
  display_name: string;
  created_at: string;
} | null> {
  if (!nativeOk()) return null;
  const { value } = await Preferences.get({ key: USER_KEY });
  if (!value) return null;
  try {
    return JSON.parse(value) as { id: string; email: string; display_name: string; created_at: string };
  } catch {
    return null;
  }
}

export async function clearOfflineUser(): Promise<void> {
  if (!nativeOk()) return;
  await Preferences.remove({ key: USER_KEY });
}

export async function saveLibraryCache(page: LibraryPage): Promise<void> {
  if (!nativeOk()) return;
  const payload: CachedLibrary = { savedAt: new Date().toISOString(), page };
  await Preferences.set({ key: META_KEY, value: JSON.stringify(payload) });
}

export async function loadLibraryCache(): Promise<LibraryPage | null> {
  if (!nativeOk()) return null;
  const { value } = await Preferences.get({ key: META_KEY });
  if (!value) return null;
  try {
    const parsed = JSON.parse(value) as CachedLibrary;
    return parsed.page ?? null;
  } catch {
    return null;
  }
}

async function ensureAudioDir(): Promise<void> {
  try {
    await Filesystem.mkdir({ path: AUDIO_DIR, directory: Directory.Data, recursive: true });
  } catch {
    /* already exists */
  }
}

export async function hasCachedAudio(uploadId: number): Promise<boolean> {
  if (!nativeOk()) return false;
  try {
    await Filesystem.stat({ path: audioPath(uploadId), directory: Directory.Data });
    return true;
  } catch {
    return false;
  }
}

/** Local WebView URI for a cached upload stream, or null. */
export async function getCachedAudioUri(uploadId: number): Promise<string | null> {
  if (!(await hasCachedAudio(uploadId))) return null;
  const { uri } = await Filesystem.getUri({ path: audioPath(uploadId), directory: Directory.Data });
  return Capacitor.convertFileSrc(uri);
}

export function uploadIdFromStreamUrl(streamUrl: string | null | undefined): number | null {
  if (!streamUrl) return null;
  const m = streamUrl.match(/\/api\/v1\/library\/(\d+)\/stream/);
  return m ? Number(m[1]) : null;
}

/** Download one library stream into Filesystem (skips if already cached). */
export async function cacheUploadAudio(upload: LibraryUpload): Promise<boolean> {
  if (!nativeOk() || !upload.song?.playback?.stream_url) return false;
  if (await hasCachedAudio(upload.id)) return true;

  const url = resolveMediaUrl(upload.song.playback.stream_url);
  if (!url) return false;

  await ensureAudioDir();
  const headers: Record<string, string> = {};
  const token = getAccessToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  try {
    // Capacitor Filesystem downloadFile writes binary without base64 round-trip.
    await Filesystem.downloadFile({
      url,
      path: audioPath(upload.id),
      directory: Directory.Data,
      headers,
    });
    return true;
  } catch (err) {
    console.warn("offline cache download failed", upload.id, err);
    return false;
  }
}

/** Persist metadata and best-effort download audio for every playable upload. */
export async function syncLibraryOffline(page: LibraryPage): Promise<void> {
  if (!nativeOk()) return;
  await saveLibraryCache(page);
  const playable = page.items.filter((u) => u.song?.playback?.stream_url);
  // Cap concurrent downloads to avoid thrashing on free phones.
  const queue = [...playable];
  const workers = Array.from({ length: Math.min(2, queue.length) }, async () => {
    while (queue.length) {
      const next = queue.shift();
      if (next) await cacheUploadAudio(next);
    }
  });
  await Promise.all(workers);
}

export async function removeCachedUpload(uploadId: number): Promise<void> {
  if (!nativeOk()) return;
  try {
    await Filesystem.deleteFile({ path: audioPath(uploadId), directory: Directory.Data });
  } catch {
    /* missing is fine */
  }
  const page = await loadLibraryCache();
  if (!page) return;
  const next: LibraryPage = {
    ...page,
    total: Math.max(0, page.total - 1),
    items: page.items.filter((u) => u.id !== uploadId),
  };
  await saveLibraryCache(next);
}

/** Resolve playback src: local file when offline/cached, else remote stream URL. */
export async function resolvePlaybackSrc(song: Song, preferLocal: boolean): Promise<string | null> {
  const stream = song.playback?.stream_url ?? null;
  if (!stream) return null;
  const uploadId = uploadIdFromStreamUrl(stream);
  if (preferLocal && uploadId != null) {
    const local = await getCachedAudioUri(uploadId);
    if (local) return local;
  }
  return resolveMediaUrl(stream) ?? stream;
}
