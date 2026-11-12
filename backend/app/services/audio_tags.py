"""Identify uploaded audio files and read their tags with mutagen."""
import base64
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import mutagen
from mutagen.flac import Picture

# Extension -> formats we accept for it (the content is sniffed; the extension alone proves nothing).
ACCEPTED_EXTENSIONS = {
    ".mp3": {"mp3"}, ".m4a": {"m4a"}, ".aac": {"aac", "m4a"}, ".flac": {"flac"},
    ".ogg": {"ogg"}, ".oga": {"ogg"}, ".wav": {"wav"},
}
CONTENT_TYPES = {
    "mp3": "audio/mpeg", "m4a": "audio/mp4", "aac": "audio/aac",
    "flac": "audio/flac", "ogg": "audio/ogg", "wav": "audio/wav",
}
MAX_COVER_BYTES = 8 * 1024 * 1024
UNKNOWN_ARTIST = "Unknown artist"


def sniff_format(head: bytes) -> str | None:
    """Audio container from the first bytes of a file, or None if it isn't one we accept."""
    if head.startswith(b"ID3"):
        return "mp3"  # ID3v2 header; mutagen confirms the stream below
    if head.startswith(b"fLaC"):
        return "flac"
    if head.startswith(b"OggS"):
        return "ogg"
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "wav"
    if head[4:8] == b"ftyp":
        return "m4a"
    if len(head) >= 2 and head[0] == 0xFF:
        if head[1] & 0xF6 == 0xF0:
            return "aac"  # ADTS: sync word + layer bits 00
        if head[1] & 0xE0 == 0xE0 and head[1] & 0x06:
            return "mp3"  # MPEG audio frame sync with a real layer
    return None


@dataclass
class Cover:
    data: bytes
    content_type: str


@dataclass
class TrackTags:
    title: str
    artists: list[str]
    album: str | None
    duration_ms: int
    genres: list[str] = field(default_factory=list)
    release_date: date | None = None
    cover: Cover | None = None
    from_filename: bool = False


class UnreadableAudio(ValueError):
    """mutagen could not parse the file as audio."""


def _clean(values) -> list[str]:
    out: list[str] = []
    for v in values or []:
        for part in re.split(r"\s*(?:;|\x00| / )\s*", str(v)):
            part = part.strip()
            if part and part not in out:
                out.append(part[:300])
    return out


def _from_filename(stem: str) -> tuple[str, list[str]]:
    """'Artist - Title' or '01 Title' style names; everything else becomes the title."""
    name = re.sub(r"[_]+", " ", stem).strip()
    name = re.sub(r"^\d{1,3}[\s.\-]+", "", name) or name
    if " - " in name:
        artist, title = name.split(" - ", 1)
        if artist.strip() and title.strip():
            return title.strip()[:300], [artist.strip()[:300]]
    return name[:300] or "Untitled", [UNKNOWN_ARTIST]


def _image_type(data: bytes, declared: str | None = None) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return declared if declared in {"image/jpeg", "image/png", "image/webp"} else None


def _cover(audio) -> Cover | None:
    candidates: list[tuple[int, bytes, str | None]] = []  # (priority, data, mime); front cover first
    tags = getattr(audio, "tags", None)
    if tags is not None and hasattr(tags, "getall"):  # ID3 (MP3, WAV)
        candidates += [(0 if f.type == 3 else 1, f.data, f.mime) for f in tags.getall("APIC")]
    if tags is not None and "covr" in getattr(tags, "keys", lambda: [])():  # MP4
        candidates += [(0, bytes(c), None) for c in tags["covr"]]
    for pic in getattr(audio, "pictures", []) or []:  # FLAC
        candidates.append((0 if pic.type == 3 else 1, pic.data, pic.mime))
    if tags is not None and hasattr(tags, "get"):  # Ogg Vorbis / Opus
        for raw in tags.get("metadata_block_picture", []) or []:
            try:
                pic = Picture(base64.b64decode(raw))
                candidates.append((0 if pic.type == 3 else 1, pic.data, pic.mime))
            except Exception:
                continue
    for _, data, mime in sorted(candidates, key=lambda c: c[0]):
        content_type = _image_type(data, mime)
        if content_type and 0 < len(data) <= MAX_COVER_BYTES:
            return Cover(data, content_type)
    return None


def _easy_tags(path: Path, audio) -> dict[str, list[str]]:
    easy = None
    try:
        easy = mutagen.File(path, easy=True)
    except Exception:
        pass
    tags = getattr(easy, "tags", None)
    out: dict[str, list[str]] = {}
    if tags is not None and hasattr(tags, "keys") and not hasattr(tags, "getall"):
        for key in ("title", "artist", "albumartist", "album", "genre", "date"):
            try:
                out[key] = list(tags.get(key) or [])
            except Exception:
                continue
    id3 = getattr(audio, "tags", None)
    if not out and id3 is not None and hasattr(id3, "getall"):  # WAV (and MP3 without EasyID3)
        for key, frame in (("title", "TIT2"), ("artist", "TPE1"), ("album", "TALB"), ("genre", "TCON"), ("date", "TDRC")):
            out[key] = [str(t) for f in id3.getall(frame) for t in f.text]
    return out


def _release_date(values: list[str]) -> date | None:
    for v in values:
        try:
            return date.fromisoformat(str(v)[:10])
        except ValueError:
            continue
    return None


def read_tags(path: Path, original_filename: str) -> TrackTags:
    """Title, artists, album, duration, genres and cover. Missing title/artist fall back to the filename."""
    try:
        audio = mutagen.File(path)
    except Exception as exc:
        raise UnreadableAudio("This file couldn't be read as audio") from exc
    if audio is None or not getattr(audio, "info", None) or not getattr(audio.info, "length", 0):
        raise UnreadableAudio("This file couldn't be read as audio")
    duration_ms = int(round(audio.info.length * 1000))
    if duration_ms <= 0:
        raise UnreadableAudio("This file has no playable audio")

    tags = _easy_tags(path, audio)
    fallback_title, fallback_artists = _from_filename(Path(original_filename).stem)
    titles = _clean(tags.get("title"))
    artists = _clean(tags.get("artist")) or _clean(tags.get("albumartist"))
    album = (_clean(tags.get("album")) or [None])[0]
    genres = [g.lower()[:100] for g in _clean(tags.get("genre"))][:5]
    return TrackTags(
        title=titles[0] if titles else fallback_title,
        artists=artists or fallback_artists,
        album=album,
        duration_ms=duration_ms,
        genres=genres,
        release_date=_release_date(tags.get("date") or []),
        cover=_cover(audio),
        from_filename=not titles,
    )
