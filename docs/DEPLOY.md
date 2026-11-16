# Deploy Spotifree (single platform)

Spotifree is **one Docker image**: Vite SPA served by FastAPI, plus **Postgres**.
Optional: Jamendo (`JAMENDO_CLIENT_ID`), Audius (`AUDIUS_*` — enabled by default for
full Open Music License streams), Cloudflare R2 (`R2_*`), and Spotify Client
Credentials (`SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET`) for **metadata-only** ML
enrichment (genres / popularity / audio-features / album + artist images — never playback).

**Chosen host: [Render](https://render.com)** free Blueprint (`render.yaml`).
[Railway](https://railway.app) remains documented as an alternative.

Do **not** split the SPA to Vercel and the API elsewhere; the production app is same-origin.

## What this repo already includes

| File | Role |
| --- | --- |
| `Dockerfile` | Multi-stage: build frontend → FastAPI image; listens on `$PORT` |
| `railway.toml` | Railway build + `/api/v1/health` check |
| `render.yaml` | Render Blueprint (web + Postgres) |
| `docker-compose.yml` | Local production-shaped stack |
| `.env.example` | All env vars (never commit `.env`) |

## Railway (recommended)

1. Push this repo to GitHub as **`priscillanjaguri/spotifreemusic`** on `main` (QH’s GitHub — not `brn-mwai`).
2. [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub** → pick `spotifreemusic`.
3. **Add PostgreSQL** in the same project; Railway injects `DATABASE_URL` into the web service (link the variable if needed).
4. Set variables on the **web** service (Variables tab):

| Variable | Required | Notes |
| --- | --- | --- |
| `SECRET_KEY` | Yes | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `DATABASE_URL` | Yes | From Postgres plugin (auto or reference) |
| `ENVIRONMENT` | Yes | `production` |
| `COOKIE_SECURE` | Yes | `true` |
| `CORS_ORIGINS` | Yes | JSON list including your public HTTPS URL **and** Capacitor origins: `["https://YOUR.up.railway.app","https://localhost","capacitor://localhost"]` |
| `JAMENDO_CLIENT_ID` | No | Discover / Creative Commons catalogue |
| `AUDIUS_ENABLED` | No | Default `true`. Set `false` to disable Audius Discover streams |
| `AUDIUS_API_HOST` | No | Default `https://api.audius.co` |
| `AUDIUS_APP_NAME` | No | Default `spotifree` (sent on every Audius request) |
| `AUDIUS_API_KEY` | No | Optional free key from https://api.audius.co/plans (higher rate limits) |
| `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` | No | Spotify Client Credentials; metadata for ML only (no streaming) |
| `GENIUS_ACCESS_TOKEN` / `GENIUS_CLIENT_*` | No | Unused for lyrics (LRCLIB is keyless). Kept optional for future Genius metadata. |
| `R2_ACCOUNT_ID` / `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` / `R2_BUCKET` | No | My Library object storage |
| `LIBRARY_ANALYSIS_ENABLED` | No | Prefer `false` on free tiers (CPU) |

5. Deploy → open the public HTTPS URL → confirm `/api/v1/health` returns `{"status":"ok",...}`.
6. Point the Android APK **Server URL** at that HTTPS origin (no trailing slash). See below.

## Render (alternative)

1. Same GitHub repo (`priscillanjaguri/spotifreemusic`) on `main`.
2. Render → **New** → **Blueprint** → select the repo (uses `render.yaml`).
3. Fill blueprint prompts for optional secrets (`CORS_ORIGINS`, Jamendo, R2, Spotify, optional `AUDIUS_API_KEY`).
4. After the first URL is known, set `CORS_ORIGINS` to include `https://<service>.onrender.com` plus Capacitor origins.
5. Audius defaults ship in `render.yaml` (`AUDIUS_ENABLED=true`, host + app name). Optional: set `AUDIUS_API_KEY` from https://api.audius.co/plans for higher limits. Set `SPOTIFY_CLIENT_ID` and `SPOTIFY_CLIENT_SECRET` for library / catalogue metadata enrichment (covers + artist photos). Leave Spotify unset to skip gracefully.
6. After merging Audius (or any catalogue change), use **Manual Deploy** on the Render web service if auto-deploy is off.
7. Backfill existing My Library covers/artist images (auth cookie or Bearer): `POST /api/v1/library/spotify-enrich?limit=200`.
8. Plain lyrics use **LRCLIB** (no API key) via `GET /api/v1/lyrics/{song_id}`. Genius env vars are optional/unused for lyric bodies.
9. Same APK Server URL steps as Railway.

## Local Docker (smoke test)

```bash
cp .env.example .env   # set SECRET_KEY; never commit .env
docker compose up --build
# → http://localhost:8000
```

## Android APK → hosted Server URL

APK artifact (Project store, not in git):
`media/android-apk/spotifree-debug.apk`

1. Install the debug APK on the phone (allow unknown sources for the installer).
2. Open **Spotifree** → **Server URL** (first launch, or Account → Server URL).
3. Enter the public HTTPS origin only, e.g. `https://spotifree-production.up.railway.app` (no `/api` path).
4. **Save & connect** → sign in / create account.

The WebView talks to that host over HTTPS; CORS must allow `https://localhost` and `capacitor://localhost`.

## Secrets

- Never commit `.env`, API keys, or DB URLs.
- Set secrets only in the host dashboard (or a local untracked `.env`).
- Cursor / chat must not paste live secret values.
