# Deploy Spotifree (single platform)

Spotifree is **one Docker image**: Vite SPA served by FastAPI, plus **Postgres**.
Optional: Jamendo (`JAMENDO_CLIENT_ID`) and Cloudflare R2 (`R2_*`).

**Chosen host (free): [Render](https://render.com)** — Blueprint (`render.yaml`): free web + free Postgres.
[Railway](https://railway.app) is optional paid (`railway.toml`); not used while staying on free tier.

Do **not** split the SPA to Vercel and the API elsewhere; the production app is same-origin.

## What this repo already includes

| File | Role |
| --- | --- |
| `Dockerfile` | Multi-stage: build frontend → FastAPI image; listens on `$PORT` |
| `railway.toml` | Railway build + `/api/v1/health` check |
| `render.yaml` | Render Blueprint (web + Postgres) |
| `docker-compose.yml` | Local production-shaped stack |
| `.env.example` | All env vars (never commit `.env`) |

## Render free (recommended)

1. Push this repo to GitHub as **`priscillanjaguri/spotifreemusic`** on `main` (QH’s GitHub — not `brn-mwai`).
2. [dashboard.render.com](https://dashboard.render.com) → **New** → **Blueprint** → connect **`priscillanjaguri/spotifreemusic`** → apply root `render.yaml`.
3. Blueprint creates free web **`spotifree`** + free Postgres **`spotifree-db`**, generates `SECRET_KEY`, sets `ENVIRONMENT=production` / `COOKIE_SECURE=true` / `LIBRARY_ANALYSIS_ENABLED=false`, and wires `DATABASE_URL`.
4. After the first public URL exists, set `CORS_ORIGINS` in the dashboard:  
   `["https://YOUR-SERVICE.onrender.com","https://localhost","capacitor://localhost"]`  
   Optional: `JAMENDO_CLIENT_ID`, `R2_*` (never commit values).
5. Confirm `/api/v1/health` → point the Android APK **Server URL** at that HTTPS origin (no trailing slash).

**Free-tier limits:** web spins down after **15 minutes** idle (~1 minute cold start); **750** free instance hours/month; free Postgres **expires after 30 days**; ephemeral filesystem.

## Railway (paid alternative)

1. Same GitHub repo on `main`.
2. [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub** → `spotifreemusic` → add Postgres → set env vars (see Project store `docs/github-and-host.md` / `.env.example`).

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
