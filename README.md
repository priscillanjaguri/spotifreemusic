# Tunewise

> Understand your music. Discover beyond it.

A personal music discovery and intelligence app: collection management, content-based
recommendations, listening analytics, taste timeline and a daily companion.

**Status: Stage 3 of 7 complete** (auth, profile, catalogue, collection, Jamendo adapter, and the web UI:
sign-in, dashboard, collection with filters, discover with search and playback).
See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for design decisions and the stage checklist.

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
Screens: **Sign in / Create account**, **Home** (stats, recently added, top genres and artists),
**Collection** (filter by artist, album, genre via `/collection/facets`; remove with undo; play all)
and **Discover** (search, add to collection, play). A persistent player bar handles playback via
the provider's stream URL. Layout: sidebar on desktop, top bar and bottom tab bar on mobile.

Design system: a "girly Spotify" look in deep satin purples (sampled from satin-ribbon references). `src/index.css` holds the palette,
font tokens (placeholder Google Fonts: Cormorant Garamond, Great Vibes, Nunito) and texture utilities
(`bg-satin-*`, `satin`, `powder`, `gloss`, `bg-cta`). See `docs/ARCHITECTURE.md` under "Stage 3 decisions".
Primitives live in `src/components/ui` (shadcn/ui), decorative motifs (rose, petals, hair waves) in
`src/components/decor.tsx`, and shared app components in `src/components`.

## API documentation
FastAPI generates it automatically: **http://localhost:8000/docs** (Swagger UI) and
`/redoc`; the raw spec is at `/openapi.json`. All routes live under `/api/v1`.

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

## API overview (all under `/api/v1`, full docs at `/docs`)
`auth/register|login|logout|me` · `profile` (PATCH, DELETE) · `profile/preferences` ·
`songs/search?q=` · `songs/{id}` · `collection` (GET with `artist_id`/`album_id`/`genre`, POST) ·
`collection/facets` · `collection/{song_id}` (DELETE). Login uses an httpOnly, SameSite=Lax cookie.
