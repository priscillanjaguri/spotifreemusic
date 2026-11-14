import type { Song } from "@/lib/types";

/** Cover art URL with graceful fallback to the primary artist's image (Spotify enrich). */
export function songArtUrl(song: Pick<Song, "cover_url" | "artists">): string | null {
  if (song.cover_url) return song.cover_url;
  for (const artist of song.artists || []) {
    if (artist.image_url) return artist.image_url;
  }
  return null;
}
