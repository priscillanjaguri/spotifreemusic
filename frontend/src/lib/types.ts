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

export type AnalysisStatus = "pending" | "running" | "done" | "failed" | "unavailable";

export type AudioFeatures = {
  tempo: number | null;
  energy: number | null;
  loudness_db: number | null;
  spectral_centroid_hz: number | null;
  key: number | null;
  mode: number | null;
  key_name: string | null;
  analyzer: string | null;
};

export type LibraryUpload = {
  id: number;
  original_filename: string;
  audio_format: string;
  size_bytes: number;
  created_at: string;
  analysis_status: AnalysisStatus;
  analysis_error: string | null;
  song: Song | null;
  features: AudioFeatures | null;
};

export type LibraryLimits = {
  accepted_extensions: string[];
  max_file_mb: number;
  max_files_per_request: number;
  storage_backend: "local" | "r2" | string;
  analysis_available: boolean;
};

export type LibraryPage = { total: number; items: LibraryUpload[]; limits: LibraryLimits };

export type UploadResult = {
  filename: string;
  status: "added" | "duplicate" | "rejected";
  message: string;
  upload: LibraryUpload | null;
};

export type Explanation = { code: string; label: string };

export type RecommendationItem = {
  song: Song;
  score: number;
  explanations: Explanation[];
};

export type RecommendationsResponse = {
  items: RecommendationItem[];
  cold_start: boolean;
  mode: "taste" | "similar" | "popular" | "genre_seed" | string;
  short_term_days: number;
  long_term_days: number;
};

export type FeedbackAction = "like" | "not_interested";

export type ListeningEventPayload = {
  song_id: number;
  started_at: string;
  ended_at: string;
  listened_ms: number;
  song_duration_ms: number;
  completed?: boolean | null;
  client_session_id?: string | null;
};
