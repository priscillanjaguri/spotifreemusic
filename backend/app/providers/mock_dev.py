"""Development-only provider: an invented catalogue with generated tones.

Enabled with DEV_MOCK_PROVIDER=true when ENVIRONMENT=development and no real provider
is configured. Everything it imports is stored with data_source='mock_dev' so the UI
labels it as sample data. It never runs in production or in the test suite.
"""
import io
import math
import wave
from array import array
from functools import lru_cache

from app.providers.base import MusicProviderAdapter, ProviderArtist, ProviderTrack

AUDIO_PATH = "/api/v1/dev/mock-audio"

# (id, title, artists, album, genres, duration_s)
_CATALOGUE: list[tuple[str, str, list[str], str | None, list[str], int]] = [
    ("m01", "Violet Hour", ["Lumen Tide"], "Afterglow Tapes", ["lofi", "chillout"], 184),
    ("m02", "Paper Lanterns", ["Lumen Tide"], "Afterglow Tapes", ["lofi", "jazz"], 201),
    ("m03", "Slow Orbit", ["Kestrel Moon"], "Low Gravity", ["ambient", "electronic"], 312),
    ("m04", "Glass Harbour", ["Kestrel Moon"], "Low Gravity", ["ambient"], 276),
    ("m05", "Neon Rain on Seventh", ["Night Arcade"], "Synthetic Weather", ["synthwave", "electronic"], 238),
    ("m06", "Overdrive Heart", ["Night Arcade", "Vera Sol"], "Synthetic Weather", ["synthwave", "pop"], 222),
    ("m07", "Blue Smoke Waltz", ["The Marlowe Trio"], "Last Set at Dawn", ["jazz"], 265),
    ("m08", "Corner Booth", ["The Marlowe Trio"], "Last Set at Dawn", ["jazz", "lounge"], 243),
    ("m09", "Wildflower Road", ["Juniper & Ash"], "Field Notes", ["folk", "acoustic"], 197),
    ("m10", "Kettle On", ["Juniper & Ash"], "Field Notes", ["folk"], 173),
    ("m11", "Static Bloom", ["Paper Satellites"], "Signal Garden", ["indie", "rock"], 214),
    ("m12", "Satellites Don't Sleep", ["Paper Satellites"], "Signal Garden", ["indie"], 229),
    ("m13", "Ivory Steps", ["Elin Moreau"], "Quiet Rooms", ["piano", "classical"], 188),
    ("m14", "Rain Study No. 3", ["Elin Moreau"], "Quiet Rooms", ["piano", "ambient"], 156),
    ("m15", "Concrete Lullaby", ["Ruff Draft", "Lumen Tide"], "Boom Bap Postcards", ["hiphop", "lofi"], 167),
    ("m16", "Late Bus Home", ["Ruff Draft"], "Boom Bap Postcards", ["hiphop"], 182),
    ("m17", "Amethyst Drive", ["Vera Sol"], None, ["pop", "electronic"], 205),
    ("m18", "Desert Radio", ["Coyote Static"], "Heatwave FM", ["rock", "blues"], 248),
    ("m19", "Copper Sun", ["Coyote Static"], "Heatwave FM", ["rock"], 233),
    ("m20", "Midnight Reverie", ["Kestrel Moon", "Elin Moreau"], "Low Gravity", ["ambient", "piano"], 341),
    ("m21", "Pulse Garden", ["Halcyon Unit"], "Biolume", ["electronic", "house"], 296),
    ("m22", "Lavender Fields", ["Halcyon Unit"], "Biolume", ["house", "chillout"], 284),
    ("m23", "Morning Chai", ["Lumen Tide"], None, ["lofi"], 149),
    ("m24", "Northern Window", ["Juniper & Ash", "Elin Moreau"], "Field Notes", ["folk", "piano"], 211),
]

_TRACKS = [
    ProviderTrack(
        provider_track_id=tid, title=title, duration_ms=secs * 1000,
        artists=[ProviderArtist(name=a) for a in artists], album_title=album, genres=genres,
        cover_url=None, stream_url=f"{AUDIO_PATH}/{tid}.wav",
        license_url="https://creativecommons.org/publicdomain/zero/1.0/",
        download_allowed=True,
    )
    for tid, title, artists, album, genres, secs in _CATALOGUE
]


class MockDevAdapter(MusicProviderAdapter):
    key = "mock_dev"
    display_name = "Development sample catalogue"
    supports_playback = True
    data_source = "mock_dev"
    is_mock = True

    def search_tracks(self, query: str, limit: int = 20) -> list[ProviderTrack]:
        words = query.lower().split()

        def haystack(t: ProviderTrack) -> str:
            return " ".join([t.title, t.album_title or "", *(a.name for a in t.artists), *t.genres]).lower()

        return [t for t in _TRACKS if all(w in haystack(t) for w in words)][:limit]


_SCALE = [0, 3, 5, 7, 10, 12, 15]  # minor pentatonic-ish, in semitones


@lru_cache(maxsize=64)
def tone_wav(track_id: str, seconds: int = 12, rate: int = 22050) -> bytes:
    """A short, soft arpeggio seeded by the track id, so each sample track sounds different."""
    seed = sum(ord(c) * (i + 1) for i, c in enumerate(track_id))
    root = 196.0 * 2 ** ((seed % 7) / 12)
    pattern = [_SCALE[(seed // (i + 1)) % len(_SCALE)] for i in range(8)]
    note_len = 0.375
    samples = array("h")
    for n in range(int(seconds * rate)):
        t = n / rate
        step = int(t / note_len)
        local = t - step * note_len
        freq = root * 2 ** (pattern[step % len(pattern)] / 12)
        envelope = math.exp(-local * 5) * min(1.0, local * 200)
        pad = 0.25 * math.sin(2 * math.pi * root / 2 * t)
        value = envelope * math.sin(2 * math.pi * freq * t) + pad
        samples.append(int(max(-1.0, min(1.0, value * 0.35)) * 32767))
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(samples.tobytes())
    return buffer.getvalue()


def is_known_track(track_id: str) -> bool:
    return any(t.provider_track_id == track_id for t in _TRACKS)
