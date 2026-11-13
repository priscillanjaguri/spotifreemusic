# Tunewise

> Understand your music. Discover beyond it.

A personal music discovery and intelligence app: collection management, content-based
recommendations, listening analytics, taste timeline and a daily companion.

**Status: Stage 7 of 7 complete** — auth, catalogue, Jamendo, My Library (local/R2), deep satin / glass UI,
content-based recommendations, listening analytics, daily companion, e2e tests, an **installable PWA**,
and a **sideloadable Android APK** (Capacitor). See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md),
[`docs/TESTING.md`](docs/TESTING.md), and [`docs/ANDROID.md`](docs/ANDROID.md).

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
Screens: **Sign in / Create account**, **Home**, **Companion**, **For You**, **Discover**,
**Collection**, **My Library**, **Analytics**. The player bar streams audio and posts listening
segments. Installable as a PWA (manifest + service worker caches the app shell only — never private
audio or `/api`).

Design system: deep satin / glass purple. Tokens in `src/index.css`. See `docs/ARCHITECTURE.md`.

## Install on Android (APK — recommended)
A Capacitor debug APK wraps the Vite UI and talks to your Tunewise backend over a configurable
**Server URL**. The phone must reach that host (same Wi‑Fi LAN IP or a deployed HTTPS URL). The
backend needs **Postgres** (and **R2** if you store library files there); Jamendo is optional.

1. Copy `tunewise-debug.apk` to the phone (USB, Drive, chat, etc.).
2. Open the file. If Android blocks it, allow **Install unknown apps** / **Unknown sources** for
   that app (Files, Chrome, Drive, …), then confirm the install.
3. Open **Tunewise**. On first launch, enter your **Server URL**, e.g.
   `http://192.168.1.20:8741` (PC LAN IP + API port) or `https://your.deployed.host`.
4. Tap **Save & connect**, then sign in. Account menu → **Server URL** changes the host later.

Rebuild locally (needs Android SDK + JDK 17+):

```bash
cd frontend
npm ci
npm run android:apk   # → android/app/build/outputs/apk/debug/app-debug.apk
```

See [`docs/ANDROID.md`](docs/ANDROID.md) for cleartext LAN notes, Bearer auth, and CORS.

## Install on Android (Chrome PWA)
Tunewise is also a Progressive Web App. On a phone:

1. Open the site in **Chrome** (HTTPS in production, or your LAN/dev URL).
2. Tap the **⋮** menu → **Install app** / **Add to Home screen** (wording varies by Chrome version).
3. Confirm. Tunewise opens full-screen (`display: standalone`) from the home-screen icon.
4. Sign in, open **My Library**, tap **Choose audio files**, upload, then play from Library / Collection.

If Chrome shows no Install option yet, use the in-app **Install Tunewise** chip when it appears, or
**Add to Home screen**. The service worker must control the page (reload once after first visit).

## Deploy (one product: SPA + API + Postgres)

**One host for the whole stack** — do not split the frontend to Vercel and the API elsewhere.
Preferred: **Railway** (`railway.toml` + `Dockerfile`). Fallback: **Render** (`render.yaml`).

Tunewise needs **Postgres** (and optionally Cloudflare R2 + a Jamendo client ID). The Docker image
builds the Vite SPA and serves it from FastAPI on `$PORT` (same origin for the PWA and browser UI).

```bash
cp .env.example .env   # set SECRET_KEY; never commit .env
# Optional: JAMENDO_CLIENT_ID, R2_*, COOKIE_SECURE=true, CORS_ORIGINS for your public URL
docker compose up --build
# → http://localhost:8000  (API + built frontend, same origin — ideal for the PWA)
```

Without Docker:

```bash
cd frontend && npm ci && npm run build && cd ..
cd backend && source .venv/bin/activate
alembic upgrade head
FRONTEND_DIST=../frontend/dist ENVIRONMENT=production \
  uvicorn app.main:app --host 0.0.0.0 --port 8000
```

`COOKIE_SECURE=true` when serving over HTTPS. Keep `JAMENDO_*` and `R2_*` in the environment only.

Full host click-path (Railway/Render env vars, health check, APK Server URL):
[`docs/DEPLOY.md`](docs/DEPLOY.md).

## API documentation
FastAPI generates it automatically: **http://localhost:8000/docs** (Swagger UI) and
`/redoc`; the raw spec is at `/openapi.json`. All routes live under `/api/v1`.

## Recommendations
Content-based picks live in `backend/app/ml/` (NumPy / Pandas / scikit-learn, no web or DB imports).

- `GET /api/v1/recommendations`
- `GET /api/v1/songs/{id}/similar`
- `POST /api/v1/feedback` (`like` | `not_interested`)
- `POST /api/v1/listening/events`

Offline metrics: `cd backend && python -m scripts.eval_recommender`

## Listening analytics & companion
- `GET /api/v1/analytics?period=week|month&offset=0` — listening time, tops, completion, daily series
- `GET /api/v1/analytics/taste-timeline?weeks=12`
- `GET /api/v1/analytics/memory-lane`
- `DELETE /api/v1/listening/history` — wipe events + playback sessions (likes/saves kept)
- `GET|POST /api/v1/companion/daily` — mood-aware briefing + playlist

Privacy: `PATCH /api/v1/profile/preferences` with `record_listening_history: false` stops new events.

## Tests
```bash
cd backend && source .venv/bin/activate
pytest
pytest tests/test_e2e_flow.py    # full product path
```
Tests run against a real PostgreSQL database (`TEST_DATABASE_URL`) built by running the
actual migrations. See [`docs/TESTING.md`](docs/TESTING.md) for the Stage 7 checklist.

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
The app only uses Jamendo's stream URLs for playback; it never downloads audio for streaming.
Licence URLs are stored so analysis only runs when permitted. Spotify is deliberately NOT used for
audio features (terms forbid feeding its content to ML models).

## My Library (your own music files)
Upload files you own (MP3, M4A/AAC, FLAC, OGG, WAV) on the **My Library** page. Each file is
validated (extension + magic bytes + mutagen), deduplicated per user by SHA-256, catalogued as a
private song, and optionally analysed with Librosa. Storage is local disk by default, or
**Cloudflare R2** when `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` and `R2_BUCKET`
are all set. See below for R2 setup. Regenerate tone fixtures with `python -m scripts.make_test_audio`.

### How to enable Cloudflare R2
1. In Cloudflare, enable **R2 Object Storage** and create a private bucket (e.g. `tunewise-music`).
2. Create an R2 API token with **Object Read & Write** scoped to that bucket; copy Access Key ID + Secret.
3. Copy your Account ID from the R2 overview.
4. Put all four values in `.env` and restart the backend. Without them, uploads stay on local disk.

## API overview (all under `/api/v1`, full docs at `/docs`)
`auth/register|login|logout|me` · `profile` (PATCH, DELETE) · `profile/preferences` ·
`songs/search?q=` · `songs/{id}` · `songs/{id}/similar` ·
`collection` (GET/POST) · `collection/facets` · `collection/{song_id}` (DELETE) ·
`library` · `library/uploads` · `library/{id}` · `library/{id}/stream` · `library/{id}/cover` ·
`recommendations` · `feedback` · `listening/events` · `listening/history` (DELETE) ·
`analytics` · `analytics/taste-timeline` · `analytics/memory-lane` ·
`companion/daily` (GET/POST).
