export type User = {
  id: string;
  email: string;
  display_name: string;
  created_at: string;
};

export type Artist = { id: number; name: string };
export type Album = { id: number; title: string };

export type Playback = {
  provider: string;
  stream_url: string;
  license_url: string | null;
};

export type Song = {
  id: number;
  title: string;
  duration_ms: number;
  artists: Artist[];
  album: Album | null;
  genres: string[];
  cover_url: string | null;
  data_source: "provider" | "mock_dev" | "user_provided" | string;
  playback: Playback | null;
};

export type SongSearchResponse = { query: string; results: Song[] };

export type CollectionSource = "search" | "recommendation" | "daily_companion" | "manual";

export type CollectionItem = {
  added_at: string;
  source: CollectionSource | string;
  song: Song;
};

export type CollectionPage = {
  total: number;
  limit: number;
  offset: number;
  items: CollectionItem[];
};

export type Facet = { id: number; name: string; count: number };

export type CollectionFacets = {
  artists: Facet[];
  albums: Facet[];
  genres: Facet[];
};

export type CollectionFilter = {
  artistId?: number;
  albumId?: number;
  genre?: string;
};
