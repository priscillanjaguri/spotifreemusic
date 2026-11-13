# Architecture (Stage 1)

## Folder structure
```
spotifree/
├── README.md  .env.example  .gitignore
├── docs/ARCHITECTURE.md
├── backend/
│   ├── app/
│   │   ├── main.py            # app factory, routers, CORS
│   │   ├── core/              # config (env), db engine/session
│   │   ├── models/            # SQLAlchemy tables, one file per domain
│   │   └── api/               # HTTP layer only: validate in, call service, shape out
│   │   ├── schemas/           # Pydantic request/response models
│   │   ├── services/          # business logic (catalogue import, collection queries)
│   │   ├── providers/         # adapter interface, Jamendo + My Library adapters, registry
│   │   ├── storage/           # object storage: local filesystem (default) or Cloudflare R2
│   │   ├── analysis/          # Librosa audio features -- pure, no web/DB/storage imports
│   │   ├── ml/                # recommender -- pure Python, no web/DB imports
│   │   ├── services/ analytics.py, companion.py   # Stage 5–6 listening intelligence
│   ├── alembic/versions/      # migrations (0001_initial_schema … 0004_recommender_…)
│   └── tests/                 # incl. test_e2e_flow.py (auth → … → companion)
└── frontend/                  # Vite + React + TS + Tailwind
    └── src/
        ├── index.css          # design tokens: purple palette, semantic CSS variables, utilities
        ├── components/ui/     # shadcn/ui primitives (Base UI), restyled through the tokens
        ├── components/        # app components: layout (shell, nav, player bar), music, states
        ├── lib/               # api client, auth + player contexts, collection / reco / analytics hooks
        └── pages/             # auth, dashboard, collection, discover, library, recommendations,
                               # analytics (Taste Timeline + Memory Lane), companion
```
Dependency direction: `api -> services -> models`, and `services -> ml` (never the reverse).
The ML package receives plain arrays/DataFrames and returns scores, so it can be unit-tested
and replaced without touching the web layer or UI.

## Database (16 tables)
| Group | Tables |
|---|---|
| Accounts | `users`, `user_preferences` |
| Catalogue (provider-independent) | `artists`, `albums`, `songs`, `song_artists`, `genres`, `song_genres`, `song_features` |
| Providers (playback side) | `music_providers`, `song_provider_links` |
| User data | `user_collections`, `user_interactions`, `playback_sessions`, `listening_events`, `library_uploads` |

### Decisions worth understanding
1. **Catalogue vs. playback are separate.** Songs never reference a provider. `song_provider_links`
   maps song -> provider track id. Adding a provider = new rows + an adapter, no schema change.
2. **`song_artists` join table** (beyond the spec's list). Collaborations ("Future & Rihanna") are
   normal; a single `artist_id` on songs would make "top artists" analytics wrong.
3. **Listening events are immutable segments with guarantees in the DB:**
   - `listened_ms` = audible time only (pauses excluded before insert).
   - An **exclusion constraint** (`btree_gist` + `tstzrange`) forbids overlapping events per user,
     enforcing "no double-counting" even if application code has a bug.
   - `play_date` is stored in the user's timezone *at listening time*, so past weekly/monthly
     reports never shift if the user moves timezone.
   - `song_duration_ms` is snapshotted so completion stays valid if metadata is later fixed.
   - Songs with history use `ON DELETE RESTRICT` -- history can't silently lose its subject.
4. **Skips are not dislikes.** `user_interactions.interaction_type` has `skipped` (neutral) and a
   separate explicit `not_interested`. There is no derived "dislike". Mood is stored only when the
   user explicitly selected it (`selected_mood`), never inferred.
5. **Interactions are an append-only log**; the latest row per target is current state. This keeps
   history for the taste timeline and lets the recommender weigh signals over time.
6. **Short- vs long-term preference** windows are per-user settings (`short_term_days`,
   `long_term_days`). Profiles themselves are computed, not stored, until performance requires it.
7. **Privacy:** every user-owned table cascades on user delete; `record_listening_history` lets a
   user stop collection; `DELETE /listening/history` wipes events + playback sessions (likes/saves stay).
8. **Labelling mock data:** `data_source` CHECK on artists/albums/songs/features
   (`mock_dev | provider | user_provided`). The UI will show a badge for `mock_dev`.
9. **IDs:** UUID for users (not enumerable); BIGINT identity for everything else (compact, fast,
   better for the high-volume `listening_events`).
10. **Text + CHECK instead of Postgres ENUMs** for type fields: adding a value is a simple
    migration rather than `ALTER TYPE` gymnastics.
11. **Analytics are computed on demand** from `listening_events` using the indexes on
    `(user_id, play_date)` / `(user_id, started_at)`. We add cached aggregate tables only if
    measurement shows they're needed.

## Stage checklist
- [x] 1 Scaffold, architecture, schema, migration, tests
- [x] 2 Backend: auth, profile, catalogue import, collection, provider interface + Jamendo adapter
- [x] 3 Frontend: design system, navigation, auth, dashboard, collection, discover
- [x] 4 Recommendation engine
- [x] 5 Listening history + weekly/monthly analytics, Taste Timeline, Memory Lane
- [x] 6 Daily companion + full integration
- [x] 7 End-to-end testing

## Stage 2 decisions
- **Auth:** Argon2id password hashes; signed JWT in an httpOnly, SameSite=Lax cookie (JS can't read it).
  Unknown-email and wrong-password logins are indistinguishable (same error, same work).
- **Search caches into our catalogue:** a search calls the provider, upserts artists/albums/songs/
  genres/provider links, then serves from our own tables. Collections reference *our* song ids only.
- **Provider not configured -> 503 with a clear message**, never fake data. Tests use a fake
  provider that exists only in the test suite.
- **Known simplification:** artists are matched by case-insensitive name (two different artists with
  the same name would merge). Revisit when we store provider artist ids.
- **Jamendo gives genre tags but no energy/valence/tempo.** Those will come from Librosa in Stage 4,
  only for tracks whose stored licence permits analysis.

## Stage 3 decisions
- **Server state lives in TanStack Query**; there is no global store. Auth (`/auth/me`) and the audio
  player are React contexts. The session stays in the httpOnly cookie; the UI only learns *who* is
  signed in from `/auth/me` and never touches the token.
- **One `<audio>` element** for the whole app, fed with the provider's `stream_url`. Songs without a
  `playback` object show a disabled play button. Each track's licence URL is linked from the player.
- **Errors are shaped once** in `lib/api.ts` (`ApiError` with `status`, `code`, readable message, including
  FastAPI 422 lists). The 503 `provider_not_configured` code gets its own screen explaining how to enable
  Jamendo; 502 and network failures get a retry state.
- **"Is this song saved?"** uses the newest 100 collection items (the API's page cap) plus songs added this
  session; a 409 on add marks older ones. A dedicated membership endpoint would remove this approximation.
- **Collection filters live in the URL** (`?artist=`, `?album=`, `?genre=`), so filtered views can be
  linked and survive reloads; artist/album/genre names in rows link into them.
- **Dev mock provider** (`DEV_MOCK_PROVIDER=true`, development only): an invented catalogue labelled
  `mock_dev` (shown as a **Sample** badge, per decision 8) with generated tones. It exists so the UI can be
  exercised without a Jamendo key; it is never selected when a real provider is configured or outside
  development. Tests still use their own fake provider.

## My Library decisions
- **A provider like any other.** `my_library` is a `MusicProviderAdapter` (never searched). Each upload
  becomes a catalogue song with a `song_provider_links` row whose `playback_uri` is our own
  `/api/v1/library/{id}/stream`, so the collection, player and future recommender need no special cases.
- **Private by construction.** `songs.owner_user_id` marks uploaded songs. `songs/{id}`, `collection`
  (POST), `library/*`, stream and cover all return 404 to anyone but the owner, so ids can't be probed.
  Artists and albums stay shared metadata, matched by name like provider imports. On delete, a user-provided
  artist or album that nothing else uses is removed too.
- **`library_uploads`** stores the file record: owner, song, SHA-256, original filename, sniffed format,
  size, storage backend and key, cover key, and analysis status. `UNIQUE (user_id, content_sha256)`
  enforces dedupe even under concurrent uploads. The same bytes from two users are two private copies.
- **Validation runs before anything is stored:**
  1. The extension must be on the allow-list.
  2. Magic bytes must match that extension (a FLAC renamed `.mp3` is rejected).
  3. The size limit is enforced while streaming to a temp file.
  4. mutagen must parse the file and find a duration.

  Rejections are per file (`status: rejected` with a reason). They never fail the whole request.
- **Storage abstraction** (`app/storage`): `put_file`, `delete`, `local_copy` (for analysis), and
  `local_path` / `presigned_url` (for serving). Local disk serves through `FileResponse`, which answers
  `Range` with 206. R2 (boto3, S3 API, `region=auto`) gets a 307 redirect to a presigned GET, so audio
  bytes never pass through the API. On delete, rows go first and files second: a stray file is harmless,
  but a row pointing at nothing is not.
- **Analysis hook.** After an upload, `BackgroundTasks` queues `run_analysis`, which moves the status
  through `pending → running → done | failed | unavailable`. It analyses the first 120 s and stores only
  measured values: tempo (left null when there's no steady beat), energy from RMS loudness, loudness dB,
  spectral centroid and roll-off, zero-crossing rate, and key/mode via Krumhansl–Schmuckler with a
  confidence score. Spotify-style danceability, valence, acousticness and instrumentalness need a
  trained model. Migration 0003 made those columns nullable rather than storing invented numbers.
  Librosa is an optional extra (`requirements-analysis.txt`). The job runs in the API process, so at
  higher volume it should move to a worker queue (RQ/Celery/Arq) behind the same function.
- **Upload UI.** The endpoint accepts many files per request. The page sends one file per request,
  two at a time, using XHR so each file gets its own progress bar. Rows poll every 2.5 s while any
  analysis is still running.
- **Legal test audio.** The fixtures are generated tones (`scripts/make_test_audio.py`). Manual testing
  used Jamendo Creative Commons tracks marked `audiodownload_allowed`. They are not committed.

## Stage 4 decisions

### How the recommender works
Spotifree recommends with **content**, not collaborative filtering. Every song becomes a vector:

1. **Tags / genres** — multi-hot from catalogue genres (always available).
2. **Audio** — Librosa numbers (tempo, energy, loudness, spectral centroid / roll-off, zero-crossing
   rate, key, mode), standardized across the candidate pool. If a song has no audio features yet,
   those dims are zeroed and ranking still works on tags alone.

Your **taste profile** is a weighted average of song vectors you engaged with:

| Signal | Weight idea | Source |
|---|---|---|
| Like (`interested`) | strongest explicit positive | feedback API |
| Save | strong | collection |
| Replay / complete / play | medium → strong | listening events from the player |
| Skip | **ignored** (neutral) | — |
| Not interested | **excluded** from candidates | feedback API |

Short-term and long-term windows come from `user_preferences.short_term_days` /
`long_term_days` (defaults 28 / 365). Profiles are computed on demand, not stored.
The two windows are blended (~60% short / 40% long).

**Ranking:** cosine similarity to the blended profile. Candidates come from (a) songs already in our
catalogue cache (including your private library), and (b) fresh tag-seeded provider searches.
Results go through **MMR** for diversity, then a light **exploration** injection so the mix does not
collapse onto one mood. Each pick gets up to two explanation chips (genre overlap, library vibe,
sound-alike, exploration, …).

**Cold start:** if there are no usable signals, use `preferred_genres` (onboarding seeds) or genres
already in your collection; if those are empty too, fall back to a “popular / rich tags” mix from the
cache.

**Jamendo analysis:** when a provider link has `download_allowed` (Jamendo’s
`audiodownload_allowed`) and a licence URL, we may temporarily download audio, run Librosa, store
`song_features`, and discard the file. Streams alone are never enough to analyse.

**Offline eval:** `python -m scripts.eval_recommender` reports precision@k, recall@k, coverage and
diversity on a synthetic catalogue (no DB/network).

API surface: `GET /recommendations`, `GET /songs/{id}/similar`, `POST /feedback`,
`POST /listening/events`. UI: **For You** on the dashboard + `/recommendations`, like / not
interested, and **More like this**.

### Design system: "girly Spotify" in deep satin purple
The theme is predominantly deep purple in a Spotify layout: floating sidebar, card grids and a persistent
player bar. All tokens live in `frontend/src/index.css`. Raw shades are Tailwind colours (`bg-royal-purple`,
`text-lavender`, ...). Components use the semantic tokens (`bg-card`, `text-heading`,
`text-muted-foreground`, `text-accent-foreground`, `text-highlight`, `ring-ring`, ...), so a re-theme only
touches that one file.

| Group | Shades |
|---|---|
| Satin ribbons (sampled from the ribbon reference), each as shadow / base / sheen | deep purple #1c0e24 / #2a1632 / #412851, royal purple #22102b / #391e47 / #522b5d, amethyst #41124f / #5c266f / #6c3480, violet #5d2f6a / #7f488e / #9461a3, plus `midnight` #140a1b and `satin-rose` #311c36 |
| Labels | `silver` #c9c0d4, `cream` #f5ece6 |
| Accents (text, highlights, small details only) | `lavender` #d9c4ef, `lilac` #d4a5e2, `mauve`, `wisteria`, `heliotrope`, `orchid-glow` #e7a3de, `purple-heart`, `rose` #f28bb3 (destructive) |

Roles:
- **Background:** the page is deep-purple shadow, with royal purple and amethyst glows behind it.
- **Surfaces:** cards are royal purple with a satin sheen (`bg-card satin`).
- **Sidebar and hero panels:** full satin ribbons (`bg-satin-deep`, `bg-satin-royal`).
- **Player bar:** `bg-satin-amethyst`.
- **Highlight tiles:** `bg-satin-violet`.
- **Text:** body text is cream, headings are a cream lilac, and muted text is a silver lilac. Links and active states use lavender, and script eyebrows use orchid-glow. All of these keep good contrast on the deep surfaces.
- **CTAs:** a glossy orchid → violet → amethyst pill (`bg-cta`).

Textures and motifs (`components/decor.tsx` plus the utilities in `index.css`):
- **Satin folds and sheen:** `bg-satin-*` and `satin`.
- **Pressed-powder grain:** `powder`, in soft-light blend.
- **Nail-polish gloss:** `gloss`.
- **Soft deep shadows:** `shadow-whip` and `shadow-whip-lg`.
- **Flowing hair-wave strands:** `<HairWaves>`.
- **Dark fabric roses and petals:** `<Rose>` and `<Petal>`, in satin tones.

Fonts (placeholders, Google Fonts via `@fontsource`) sit behind tokens:
- `--font-display`: Cormorant Garamond.
- `--font-script`: Great Vibes, for the logo, eyebrows and accents.
- `--font-sans`: Nunito.

To swap a font, change its `@import` and its token.

Component variants: Button `cta` (glossy pill), Badge `genre`, `highlight` and `mock`. `SongCard` provides the
Spotify-style tiles on the dashboard.

## Stage 5 decisions
- **Analytics on demand** from `listening_events` (no aggregate tables). Period windows use the user's
  `timezone` and `week_starts_on`. Completion rate ignores events where `completed` is NULL.
- **Taste Timeline** rolls weekly genre share + listening totals and surfaces milestones (first listen /
  like / save, most-replayed) from the append-only interaction log and events.
- **Memory Lane** mixes on-this-day / last-week flashbacks, rediscoveries (gap ≥ 14 days between plays),
  firsts and favourites. Items are playable when a stream exists.
- **Privacy UI** on Analytics: toggle `record_listening_history` and `DELETE /api/v1/listening/history`.
  The player already posts audible-only segments with `client_session_id` for idempotent sessions.

## Stage 6 decisions
- **Daily companion** (`GET/POST /companion/daily`) builds a briefing + playlist via the Stage 4
  recommender, optionally nudged by an explicit mood (`soft` / `dreamy` / `focus` / `energy` /
  `chill` / `glow`) that temporarily blends genre seeds — mood is never inferred.
- **Navigation** lists Home, Companion, For You, Discover, Collection, My Library, Analytics as one
  product. Mobile keeps four primaries + a More sheet for Collection / Library / Analytics.
- **Integration:** Jamendo (or mock_dev) search, My Library uploads, R2/local streaming, recommender,
  listening events and analytics all share the same catalogue song ids and player.

## Stage 7 decisions
- **Backend e2e** lives in `tests/test_e2e_flow.py` (auth → search → collect → listen → feedback →
  recommendations → analytics → companion → history wipe). Domain suites cover analytics and companion.
- **Frontend verification:** `npm run typecheck` / `npm run build`, plus manual / screenshot passes of
  the purple product surfaces. See README “Tests” and `docs/TESTING.md`.
