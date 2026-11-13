# Spotifree Android APK (Capacitor)

The Vite/React UI is packaged with **Capacitor** into a native Android WebView app
(`com.spotifree.app`). It is a real APK for sideloading — not a PWA shortcut.

## What you need on the phone path

| Piece | Required |
| --- | --- |
| Spotifree API (FastAPI) reachable from the phone | Yes |
| PostgreSQL behind that API | Yes |
| Cloudflare R2 | Only if library files are stored in R2 |
| Jamendo client ID | Optional (Discover / CC catalogue) |

Production / sideload APKs default to the hosted API
**`https://spotifree-rw0a.onrender.com`** (no Server URL step required). Override in-app if you
point at a LAN machine or another host (see [`DEPLOY.md`](DEPLOY.md)).


## Install the debug APK

1. Transfer `spotifree-debug.apk` to the device.
2. Allow **Install unknown apps** for the installer you used (Files / Chrome / Drive / …).
3. Install and open **Spotifree** — it connects to `https://spotifree-rw0a.onrender.com` by default.
4. Optional: **Server URL** settings if you need a LAN IP (`http://192.168.x.x:8741`) or another host.
5. Sign in. Uploads and playback go to that API (Bearer token + optional `?access_token=` for `<audio>` / cover URLs).

## Build from source

```bash
# Android SDK + platform-tools + JDK 17+ on PATH; ANDROID_HOME set
cd frontend
npm ci
npm run android:apk
# APK: android/app/build/outputs/apk/debug/app-debug.apk
```

`frontend/.env.production` sets `VITE_API_BASE_URL=https://spotifree-rw0a.onrender.com` for
`vite build` / `android:apk`. Override for a one-off build:

```bash
VITE_API_BASE_URL=https://music.example.com npm run android:apk
```

## How the APK talks to the API

- The WebView loads bundled `dist/` assets (`https://localhost` scheme).
- API calls use `VITE_API_BASE_URL` / production default, or the in-app **Server URL** (`localStorage`).
- Login/register return an `access_token`; the client sends `Authorization: Bearer …`.
  Cookies still work for the browser / same-origin SPA.
- Cleartext HTTP to LAN IPs is allowed in the debug APK (`usesCleartextTraffic` + network security config).
- CORS must allow Capacitor origins (`https://localhost`, `capacitor://localhost`). Defaults and
  `.env.example` include these; production `CORS_ORIGINS` should too.
- **My Library uploads** on the APK use `@capawesome/capacitor-file-picker` (not the WebView
  `<input type="file">`), with `launchMode=singleTop` and `READ_MEDIA_AUDIO` so picking from
  Downloads keeps the selection when returning to the app.

## Status bar

Deep purple `#2a0a3d` via `@capacitor/status-bar` and Android theme colors.
