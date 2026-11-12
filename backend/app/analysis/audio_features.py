"""Measurable audio features via Librosa (optional dependency: requirements-analysis.txt).

Only values Librosa can actually measure are produced. Spotify-style danceability, valence,
acousticness and instrumentalness need a trained model and are deliberately left out.
"""
from dataclasses import asdict, dataclass
from importlib.util import find_spec
from pathlib import Path

# Analyse at most this much audio (from the start) to bound CPU time on long files.
MAX_SECONDS = 120.0
SAMPLE_RATE = 22050

# Krumhansl-Schmuckler key profiles (major, minor), index 0 = tonic.
_MAJOR = (6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88)
_MINOR = (6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17)
PITCH_CLASSES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


class AnalysisUnavailable(Exception):
    """Librosa (or its audio decoders) is not installed."""


@dataclass(frozen=True)
class AudioFeatures:
    tempo: float | None  # BPM; None when no steady beat (e.g. a sustained tone)
    energy: float  # 0..1, from RMS loudness
    rms: float
    loudness_db: float
    spectral_centroid_hz: float
    spectral_rolloff_hz: float
    zero_crossing_rate: float
    key: int | None  # 0 = C ... 11 = B
    mode: int | None  # 1 = major, 0 = minor
    key_confidence: float | None  # correlation with the best key profile, -1..1
    analyzer: str

    def as_dict(self) -> dict:
        return asdict(self)

    @property
    def key_name(self) -> str | None:
        if self.key is None or self.mode is None:
            return None
        return f"{PITCH_CLASSES[self.key]} {'major' if self.mode == 1 else 'minor'}"


def librosa_available() -> bool:
    return find_spec("librosa") is not None


def estimate_key(chroma_mean) -> tuple[int | None, int | None, float | None]:
    """Best-matching (key, mode, correlation) for a 12-bin mean chroma vector."""
    import numpy as np

    chroma = np.asarray(chroma_mean, dtype=float)
    if chroma.shape != (12,) or not np.any(chroma > 0) or np.allclose(chroma, chroma[0]):
        return None, None, None
    best = (None, None, -2.0)
    for mode, profile in ((1, _MAJOR), (0, _MINOR)):
        for tonic in range(12):
            r = float(np.corrcoef(chroma, np.roll(profile, tonic))[0, 1])
            if r > best[2]:
                best = (tonic, mode, r)
    return best


def energy_from_rms(rms: float) -> float:
    """Map mean RMS amplitude onto 0..1 via loudness: -60 dBFS -> 0, 0 dBFS -> 1."""
    import math

    if rms <= 0:
        return 0.0
    return min(1.0, max(0.0, (20 * math.log10(rms) + 60) / 60))


def analyze_file(path: Path, max_seconds: float = MAX_SECONDS) -> AudioFeatures:
    """Decode up to `max_seconds` of `path` and measure it. Raises AnalysisUnavailable or ValueError."""
    if not librosa_available():
        raise AnalysisUnavailable("Install backend/requirements-analysis.txt to enable audio analysis")
    import librosa
    import numpy as np

    try:
        y, sr = librosa.load(str(path), sr=SAMPLE_RATE, mono=True, duration=max_seconds)
    except Exception as exc:  # decoder errors vary by backend (soundfile, audioread/ffmpeg)
        raise ValueError(f"Could not decode audio: {exc.__class__.__name__}") from exc
    if y.size < sr // 2:
        raise ValueError("Audio is shorter than half a second")

    rms = float(np.mean(librosa.feature.rms(y=y)))
    tempo_arr, beats = librosa.beat.beat_track(y=y, sr=sr)
    tempo = float(np.atleast_1d(tempo_arr)[0])
    if len(beats) < 4 or not 30 <= tempo <= 300:
        tempo = None
    key, mode, confidence = estimate_key(librosa.feature.chroma_cqt(y=y, sr=sr).mean(axis=1))

    return AudioFeatures(
        tempo=round(tempo, 2) if tempo else None,
        energy=round(energy_from_rms(rms), 4),
        rms=round(rms, 6),
        loudness_db=round(20 * float(np.log10(max(rms, 1e-10))), 2),
        spectral_centroid_hz=round(float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))), 2),
        spectral_rolloff_hz=round(float(np.mean(librosa.feature.spectral_rolloff(y=y, sr=sr))), 2),
        zero_crossing_rate=round(float(np.mean(librosa.feature.zero_crossing_rate(y))), 6),
        key=key,
        mode=mode,
        key_confidence=round(confidence, 4) if confidence is not None else None,
        analyzer=f"librosa-{librosa.__version__}",
    )
