"""Genius API client — plain lyrics lookup (metadata search + song-page extract).

Auth: prefer a Client Access Token as Bearer. When only Client ID + Client Secret
are available (or the provided token is actually a Client ID), use OAuth
client-credentials against https://api.genius.com/oauth/token.

The public Genius API returns song metadata + URL, not the lyric body. We fetch
the official song page HTML server-side and extract ``data-lyrics-container``
nodes — the same pattern used by Genius client apps with a token + song URL.
Never expose tokens to the frontend.
"""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from html.parser import HTMLParser

import httpx

from app.providers.base import ProviderError

log = logging.getLogger(__name__)

API_BASE = "https://api.genius.com"
TOKEN_URL = f"{API_BASE}/oauth/token"
PAGE_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


@dataclass(frozen=True)
class GeniusSongHit:
    id: int
    title: str
    artist: str
    url: str


@dataclass
class GeniusClient:
    """Genius search + lyrics. Safe to construct only when credentials exist."""

    # Direct Client Access Token (Bearer), and/or Client ID used with client_secret.
    access_token: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    http: httpx.Client = field(default_factory=lambda: httpx.Client(timeout=25.0, follow_redirects=True))
    _bearer: str | None = field(default=None, init=False, repr=False)
    _bearer_expires_at: float = field(default=0.0, init=False, repr=False)

    def close(self) -> None:
        self.http.close()

    @property
    def configured(self) -> bool:
        return bool(self.access_token or (self.client_id and self.client_secret))

    def _ensure_bearer(self) -> str:
        now = time.time()
        if self._bearer and now < self._bearer_expires_at - 30:
            return self._bearer

        # Path A: Client ID + Secret → OAuth client credentials.
        cid = self.client_id or (self.access_token if self.client_secret else None)
        if cid and self.client_secret:
            try:
                resp = self.http.post(
                    TOKEN_URL,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": cid,
                        "client_secret": self.client_secret,
                    },
                )
                resp.raise_for_status()
                payload = resp.json()
            except (httpx.HTTPError, ValueError) as exc:
                raise ProviderError(f"Genius token request failed: {exc.__class__.__name__}") from exc
            token = payload.get("access_token")
            if not isinstance(token, str) or not token:
                raise ProviderError("Genius token response missing access_token")
            self._bearer = token
            # Genius often omits expires_in; default to 1h.
            expires_in = int(payload.get("expires_in") or 3600)
            self._bearer_expires_at = now + max(60, expires_in)
            return self._bearer

        # Path B: raw Client Access Token as Bearer.
        if self.access_token:
            self._bearer = self.access_token
            self._bearer_expires_at = now + 3600
            return self._bearer

        raise ProviderError("Genius is not configured")

    def _api_get(self, path: str, params: dict | None = None) -> dict:
        token = self._ensure_bearer()
        try:
            resp = self.http.get(
                f"{API_BASE}{path}",
                params=params,
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            )
            resp.raise_for_status()
            payload = resp.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderError(f"Genius API request failed: {exc.__class__.__name__}") from exc
        meta = payload.get("meta") or {}
        if meta.get("status") not in (None, 200):
            raise ProviderError(f"Genius API error: {meta.get('message') or meta.get('status')}")
        return payload.get("response") or {}

    def search_song(self, title: str, artist: str) -> GeniusSongHit | None:
        query = " ".join(p for p in (title.strip(), artist.strip()) if p)
        if not query:
            return None
        response = self._api_get("/search", {"q": query})
        hits = response.get("hits") or []
        best: GeniusSongHit | None = None
        title_l = title.strip().lower()
        artist_l = artist.strip().lower()
        for hit in hits:
            if (hit or {}).get("type") not in (None, "song"):
                continue
            row = (hit or {}).get("result") or {}
            try:
                song_id = int(row["id"])
                song_title = str(row.get("title") or "").strip()
                primary = row.get("primary_artist") or {}
                song_artist = str(primary.get("name") or "").strip()
                url = str(row.get("url") or "").strip()
            except (KeyError, TypeError, ValueError):
                continue
            if not (song_id and song_title and url):
                continue
            candidate = GeniusSongHit(id=song_id, title=song_title, artist=song_artist, url=url)
            # Prefer title+artist overlap; otherwise first usable hit.
            if title_l and title_l in song_title.lower() and (not artist_l or artist_l in song_artist.lower()):
                return candidate
            if best is None:
                best = candidate
        return best

    def fetch_lyrics(self, song_url: str) -> str | None:
        """Fetch the Genius song page and extract plain lyrics text."""
        if not song_url.startswith("https://genius.com/"):
            raise ProviderError("Refusing to fetch lyrics from a non-Genius URL")
        html = self._fetch_song_html(song_url)
        if _looks_like_challenge(html):
            raise ProviderError("Genius page fetch blocked (challenge page)")
        text = extract_lyrics_from_html(html)
        return text or None

    def _fetch_song_html(self, song_url: str) -> str:
        """Prefer curl_cffi Chrome impersonation; fall back to httpx."""
        headers = {
            "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://genius.com/",
        }
        try:
            from curl_cffi import requests as creq

            resp = creq.get(
                song_url,
                headers=headers,
                impersonate="chrome124",
                timeout=30,
                allow_redirects=True,
            )
            if resp.status_code >= 400:
                raise ProviderError(f"Genius page HTTP {resp.status_code}")
            return resp.text
        except ProviderError:
            raise
        except Exception as exc:
            log.info("curl_cffi Genius fetch failed (%s); trying httpx", exc.__class__.__name__)

        try:
            resp = self.http.get(
                song_url,
                headers={**headers, "User-Agent": PAGE_UA},
            )
            resp.raise_for_status()
            return resp.text
        except httpx.HTTPError as exc:
            raise ProviderError(f"Genius page fetch failed: {exc.__class__.__name__}") from exc


def _looks_like_challenge(html: str) -> bool:
    sample = html[:4000].lower()
    return (
        "cf-browser-verification" in sample
        or "just a moment" in sample
        or "cdn-cgi/challenge" in sample
        or ("cloudflare" in sample and "data-lyrics-container" not in html)
    )


class _LyricsHTMLParser(HTMLParser):
    """Pull text from Genius ``data-lyrics-container`` / ``Lyrics__Container`` nodes."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_d = {k: (v or "") for k, v in attrs}
        classes = attrs_d.get("class", "")
        is_container = attrs_d.get("data-lyrics-container") == "true" or "Lyrics__Container" in classes
        if is_container and self._depth == 0:
            self._depth = 1
            return
        if self._depth > 0:
            self._depth += 1
            if tag == "br":
                self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if self._depth <= 0:
            return
        if tag in ("div", "p", "h1", "h2", "h3"):
            self.parts.append("\n")
        self._depth -= 1

    def handle_data(self, data: str) -> None:
        if self._depth > 0:
            self.parts.append(data)


_INSTRUMENTAL = re.compile(r"^\s*\[instrumental\]\s*$", re.I)
_EXTRA_BLANK = re.compile(r"\n{3,}")


def extract_lyrics_from_html(html: str) -> str:
    parser = _LyricsHTMLParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        log.debug("Genius HTML parse failed", exc_info=True)
        return ""
    text = "".join(parser.parts)
    # Strip leftover annotation chrome Genius sometimes leaves in the DOM.
    text = text.replace("\xa0", " ")
    text = _EXTRA_BLANK.sub("\n\n", text).strip()
    if _INSTRUMENTAL.match(text):
        return ""
    return text
