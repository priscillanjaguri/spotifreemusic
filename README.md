# Tunewise

> Understand your music. Discover beyond it.

A personal music discovery and intelligence app: collection management, content-based
recommendations, listening analytics, taste timeline and a daily companion.

**Status: Stage 4 of 7 complete** — Stages 1–3 (auth, catalogue, Jamendo, deep-satin-purple UI, My Library)
plus the **content-based recommendation engine**: taste profiles, For You / similar tracks, like & not
interested, listening events from the player, and offline eval metrics.
See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for design decisions and a plain-language
“How the recommender works” section.

## Stack
React + TypeScript + Vite + Tailwind v4 + shadcn/ui (Base UI) + TanStack Query (frontend) · FastAPI + Pydantic (backend) ·
PostgreSQL + SQLAlchemy 2 + Alembic · NumPy / Pandas / scikit-learn (recommender).

## Prerequisites
Python 3.11+, Node 20+, PostgreSQL 14+ (with the `contrib` package, which provides `btree_gist`).

## Setup

```bash
# 1. Database (once)
createuser --pwprompt tunewise
createdb -O tunewise tunewise
createdb -O tunewise tunewise_test      # tests WIPE this database; keep it separate

# 2. Configuration
cp .env.example .env                    # then edit: passwords + SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(48))"   # paste as SECRET_KEY

# 3. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
pip install -r requirements-analysis.txt   # optional: Librosa audio analysis for My Library
alembic upgrade head                    # create tables via migrations
uvicorn app.main:app --reload           # http://localhost:8000

# 4. Frontend (new terminal)
cd frontend
npm install
npm run dev                             # http://localhost:5173 (proxies /api to :8000)
```

The dev server proxies `/api` to `http://localhost:8000`; set `TUNEWISE_API_URL` to point it elsewhere,
e.g. `TUNEWISE_API_URL=http://localhost:8741 npm run dev -- --port 5791`.

### Trying the UI without a Jamendo key
Set `DEV_MOCK_PROVIDER=true` in `.env` (only honoured when `ENVIRONMENT=development` and
`JAMENDO_CLIENT_ID` is empty). Search then serves a small invented catalogue, stored with
`data_source='mock_dev'` and shown with a **Sample** badge, and playback streams generated
12-second tones from `/api/v1/dev/mock-audio/…`. Leave it off to see the real "provider not
configured" (503) state in Discover.

## Frontend
```bash
cd frontend
npm run typecheck     # tsc, no emit
npm run build         # typecheck + production bundle in dist/
```
Screens: **Sign in / Create account**, **Home** (stats, **For You**, recently added, top genres/artists),
**For You** (`/recommendations` — seed genres, likes / not interested, More like this),
**Collection**, **Discover**, and **My Library**. The player bar streams audio and quietly posts
listening segments so taste profiles can learn from plays, completes and replays.

Design system: a "girly Spotify" look in deep satin purples (sampled from satin-ribbon references). `src/index.css` holds the palette,
font tokens (placeholder Google Fonts: Cormorant Garamond, Great Vibes, Nunito) and texture utilities
(`bg-satin-*`, `satin`, `powder`, `gloss`, `bg-cta`). See `docs/ARCHITECTURE.md` under "Stage 3 decisions".
Primitives live in `src/components/ui` (shadcn/ui), decorative motifs (rose, petals, hair waves) in
`src/components/decor.tsx`, and shared app components in `src/components`.

## API documentation
FastAPI generates it automatically: **http://localhost:8000/docs** (Swagger UI) and
`/redoc`; the raw spec is at `/openapi.json`. All routes live under `/api/v1`.

## Recommendations
Content-based picks live in `backend/app/ml/` (NumPy / Pandas / scikit-learn, no web or DB imports).
Services load signals and candidates, call `ml/`, and expose:

- `GET /api/v1/recommendations`
- `GET /api/v1/songs/{id}/similar`
- `POST /api/v1/feedback` (`like` | `not_interested`)
- `POST /api/v1/listening/events`

Offline metrics (synthetic catalogue, no network):

```bash
cd backend && source .venv/bin/activate
python -m scripts.eval_recommender
```

## Tests
```bash
cd backend && source .venv/bin/activate
pytest
```
Tests run against a real PostgreSQL database (`TEST_DATABASE_URL`) built by running the
actual migrations, so they also verify the migrations and Postgres-only constraints.

## Migrations
```bash
alembic revision --autogenerate -m "describe change"   # then REVIEW the generated file
alembic upgrade head
alembic downgrade -1
```
Production never calls `create_all()`; the schema only changes through migrations.

## Music data & playback (important)
Real music comes from **Jamendo** (Creative Commons catalogue). Get a free client ID at
https://developer.jamendo.com and set `JAMENDO_CLIENT_ID` in `.env`. Without it the app still runs,
but search/playback report "provider not configured" (HTTP 503) rather than faking anything.

Verify the live connection (needs internet):
```bash
cd backend && python -m scripts.check_jamendo chill
```
The app only uses Jamendo's stream URLs for playback; it never downloads audio. Each track's
licence URL is stored so we can check it before any audio analysis (Librosa, planned).
Spotify is deliberately NOT used for audio features (its terms forbid feeding its content to ML
models, and the audio-features endpoint is closed to new apps).

## My Library (your own music files)
Upload files you own (MP3, M4A/AAC, FLAC, OGG, WAV) on the **My Library** page: drag and drop, or
**Add music** on mobile. Each file is:
- **Checked:** the extension must be accepted and the content must really be that format (magic bytes,
  then mutagen). There is a size limit, `LIBRARY_MAX_FILE_MB` (default 200).
- **Deduplicated per user** by SHA-256. Re-uploading the same bytes reports "Already in your library".
- **Tagged** with mutagen: title, artists, album, genre, date, duration and embedded cover art. When there
  are no tags it falls back to the filename (`Artist - Title.mp3`).
- **Catalogued** as a private song (`data_source='user_provided'`, `songs.owner_user_id`) and added to
  your collection, so it plays in the normal player. Other users get 404 for it everywhere.
- **Analysed** in the background with Librosa: tempo, energy/RMS, loudness, spectral centroid and
  roll-off, zero-crossing rate, and key/mode. The results go into `song_features`. This is optional:
  install `requirements-analysis.txt`. Without it, files still upload and play and show "Not analysed".
  `ffmpeg` on the PATH lets it decode M4A/AAC.

Files are stored under `var/library/` (git-ignored; change it with `LIBRARY_STORAGE_DIR`), or in
Cloudflare R2 when configured. Streaming is owner-only. Local files support HTTP Range requests,
so seeking works. With R2 the stream URL redirects to a presigned URL that expires after
`R2_PRESIGN_SECONDS` (default 600). Deleting a file removes the stored objects and the song,
plus its album and artists if nothing else uses them.

Regenerate the test fixtures (generated tones only) with `python -m scripts.make_test_audio`.

### How to enable Cloudflare R2
You need to create two things in Cloudflare: **an R2 bucket** and **an R2 API token** for it.

1. In the Cloudflare dashboard, open **R2 Object Storage** and enable it. Cloudflare asks for a payment
   method even for the free tier.
2. **Create a bucket**, for example `tunewise-music`. Leave it private: don't connect a custom domain
   and don't enable the public `r2.dev` URL. Playback uses short-lived presigned URLs instead.
3. Go to **R2 → Manage R2 API Tokens → Create API token**:
   - Permission: **Object Read & Write**.
   - Scope: **Apply to specific buckets only**, pick your bucket.
   - TTL: as you prefer.

   Create it, then copy the **Access Key ID** and **Secret Access Key**. The secret is shown only once.
4. Copy your **Account ID** from the R2 overview page (right-hand side).
5. Put the four values in `.env` and restart the backend:
   ```
   R2_ACCOUNT_ID=<account id>
   R2_ACCESS_KEY_ID=<access key id>
   R2_SECRET_ACCESS_KEY=<secret access key>
   R2_BUCKET=tunewise-music
   ```

R2 is used only when all four are set; otherwise uploads go to the local disk. No bucket CORS rule is
needed for playback, because the `<audio>` element follows the redirect without CORS. Add a GET rule for
your site's origin only if you later read the files with `fetch` or Web Audio. Files uploaded before
switching stay on the old backend: they report `storage_mismatch` (503) until they're re-uploaded.

## API overview (all under `/api/v1`, full docs at `/docs`)
`auth/register|login|logout|me` · `profile` (PATCH, DELETE) · `profile/preferences` ·
`songs/search?q=` · `songs/{id}` · `collection` (GET with `artist_id`/`album_id`/`genre`, POST) ·
`collection/facets` · `collection/{song_id}` (DELETE) · `library` (GET) · `library/uploads` (POST, multipart
`files`) · `library/{id}` (GET, DELETE) · `library/{id}/stream` (Range) · `library/{id}/cover`. Login uses an httpOnly, SameSite=Lax cookie.
