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

Point the app at your LAN machine or a **single-platform HTTPS host** (Railway or Render — see
[`DEPLOY.md`](DEPLOY.md)). After deploy, set **Server URL** to the public origin
(e.g. `https://….up.railway.app`) with no path suffix.


## Install the debug APK

1. Transfer `spotifree-debug.apk` to the device.
2. Allow **Install unknown apps** for the installer you used (Files / Chrome / Drive / …).
3. Install and open **Spotifree**.
4. Set **Server URL** to something the phone can open, for example:
   - Same Wi‑Fi: `http://192.168.x.x:8741` (run the API with `--host 0.0.0.0`)
   - Deployed: `https://music.example.com`
5. Sign in. Uploads and playback go to that API (Bearer token + optional `?access_token=` for `<audio>` / cover URLs).

## Build from source

```bash
# Android SDK + platform-tools + JDK 17+ on PATH; ANDROID_HOME set
cd frontend
npm ci
npm run android:apk
# APK: android/app/build/outputs/apk/debug/app-debug.apk
```

Optional build-time default (still overridable in-app):

```bash
VITE_API_BASE_URL=https://music.example.com npm run android:apk
```

## How the APK talks to the API

- The WebView loads bundled `dist/` assets (`https://localhost` scheme).
- API calls use `VITE_API_BASE_URL` or the in-app **Server URL** (`localStorage`).
- Login/register return an `access_token`; the client sends `Authorization: Bearer …`.
  Cookies still work for the browser / same-origin SPA.
- Cleartext HTTP to LAN IPs is allowed in the debug APK (`usesCleartextTraffic` + network security config).
- CORS must allow Capacitor origins (`https://localhost`, `capacitor://localhost`). Defaults and
  `.env.example` include these; production `CORS_ORIGINS` should too.

## Status bar

Deep purple `#2a0a3d` via `@capacitor/status-bar` and Android theme colors.
