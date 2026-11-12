# Tunewise

> Understand your music. Discover beyond it.

A personal music discovery and intelligence app: collection management, content-based
recommendations, listening analytics, taste timeline and a daily companion.

**Status: Stage 7 of 7 complete** — auth, catalogue, Jamendo, My Library (local/R2), deep-satin-purple UI,
content-based recommendations, listening history + weekly/monthly analytics (Taste Timeline, Memory Lane),
daily companion, and end-to-end test coverage. See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) and
[`docs/TESTING.md`](docs/TESTING.md).

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
**Collection**, **My Library**, **Analytics** (weekly/monthly charts, Taste Timeline, Memory Lane, privacy).
The player bar streams audio and posts listening segments so taste profiles and analytics can learn
from plays, completes and replays.

Design system: a "girly Spotify" look in deep satin purples. `src/index.css` holds the palette,
font tokens (Cormorant Garamond, Great Vibes, Nunito) and texture utilities
(`bg-satin-*`, `satin`, `powder`, `gloss`, `bg-cta`). See `docs/ARCHITECTURE.md`.

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
