# Spotifree Android APK (Capacitor)

The Vite/React UI is packaged with **Capacitor** into a native Android WebView app
(`com.spotifree.app`). It is a real APK for sideloading — not a PWA shortcut.

## Online vs offline

| Mode | UI | My Library | Discover / Jamendo+Audius / lyrics / eval / companion cloud |
| --- | --- | --- | --- |
| **Online** | Live SPA from Render (`server.url`) — UI updates without APK reinstall | Sync metadata + download audio into device cache | Need network |
| **Offline** | Bundled `dist/` shell (`MainActivity` skips `server.url`; `errorPath` safety net) | Cached list + local Filesystem playback | Unavailable |

**Offline works for:** opening the app, signing in with a previously cached session, browsing **My Library** from Preferences cache, playing uploads already downloaded to Filesystem.

**Still need network for:** first login, uploads, Jamendo/Audius Discover, recommendations, analytics refresh, companion, lyrics, `/eval`, Spotify enrichment.

Cache stack: `@capacitor/preferences` (library JSON + user), `@capacitor/filesystem` (audio under `library-audio/`), `@capacitor/network` (banner + status).

## What you need on the phone path

| Piece | Required |
| --- | --- |
| Spotifree API (FastAPI) reachable from the phone | For online features |
| PostgreSQL behind that API | Yes (server-side) |
| Cloudflare R2 | Only if library files are stored in R2 |
| Jamendo client ID | Optional (Discover / CC catalogue) |
| Audius | On by default (no key); optional `AUDIUS_API_KEY` |

Production / sideload APKs prefer the **live web UI** from
**`https://spotifree-rw0a.onrender.com`** when the device has network. Override in-app
**Server URL** for a LAN API host ([`DEPLOY.md`](DEPLOY.md)).

**Reinstall the APK** after native / offline-shell changes. Pure Render SPA tweaks still
ship without reinstall when online.


## Install the debug APK

1. Transfer `spotifree-debug.apk` to the device.
2. Allow **Install unknown apps** for the installer you used (Files / Chrome / Drive / …).
3. Install and open **Spotifree**.
4. Online: WebView loads Render. Offline: local shell + cached library (if you used Library while online before).
5. Optional: **Server URL** settings for a LAN IP (`http://192.168.x.x:8741`).
6. Sign in once online so the session + library can be cached for offline.

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

- **Online:** WebView loads Render (`server.url`). Capacitor injects the native bridge into that remote page.
- **Offline:** `MainActivity` loads bundled `webDir` (`dist/`). `server.errorPath=index.html` also covers Render timeouts while “online”.
- API calls use `VITE_API_BASE_URL` / `DEFAULT_HOSTED_API_BASE`, or the in-app **Server URL**.
- Login/register return an `access_token`; the client sends `Authorization: Bearer …`.
- Cleartext HTTP to LAN IPs is allowed (`usesCleartextTraffic` + network security config).
- **My Library uploads** use `@capawesome/capacitor-file-picker` with `launchMode=singleTop` and `READ_MEDIA_AUDIO`.

## Status bar

Deep purple `#2a0a3d` via `@capacitor/status-bar` and Android theme colors.
