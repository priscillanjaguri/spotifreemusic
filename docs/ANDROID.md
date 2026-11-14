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

Production / sideload APKs load the **live web UI** from
**`https://spotifree-rw0a.onrender.com`** (`capacitor.config.ts` → `server.url`) and talk to the
same origin for API calls (no Server URL step required). Override in-app if you point at a LAN
machine or another host (see [`DEPLOY.md`](DEPLOY.md)).

**Reinstall once** after switching to live UI; after that, frontend/UI changes deploy via Render
without a new APK. Offline phones will not show the UI. Native-only changes (plugins, permissions,
manifest) still need an APK rebuild.


## Install the debug APK

1. Transfer `spotifree-debug.apk` to the device.
2. Allow **Install unknown apps** for the installer you used (Files / Chrome / Drive / …).
3. Install and open **Spotifree** — WebView loads `https://spotifree-rw0a.onrender.com` (needs network).
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

- The WebView loads the **live SPA** from `server.url` (`https://spotifree-rw0a.onrender.com`), not
  bundled `dist/` as the primary UI (`webDir` remains for Capacitor sync / offline fallback assets).
- API calls use the same origin by default (`VITE_API_BASE_URL` / `DEFAULT_HOSTED_API_BASE`), or the
  in-app **Server URL** (`localStorage`).
- Login/register return an `access_token`; the client sends `Authorization: Bearer …`.
  Cookies work for the same-origin SPA in the WebView.
- Cleartext HTTP to LAN IPs is allowed in the debug APK (`usesCleartextTraffic` + network security config).
- Navigation is allowlisted to `spotifree-rw0a.onrender.com` via `server.allowNavigation`.
- Native plugins (Capawesome FilePicker, StatusBar, …) keep working — Capacitor injects the bridge
  into the remote WebView.
- **My Library uploads** on the APK use `@capawesome/capacitor-file-picker` (not the WebView
  `<input type="file">`), with `launchMode=singleTop` and `READ_MEDIA_AUDIO` so picking from
  Downloads keeps the selection when returning to the app.

## Status bar

Deep purple `#2a0a3d` via `@capacitor/status-bar` and Android theme colors.
