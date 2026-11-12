"""Generate the tagged test-audio fixtures (generated tones only, no recorded music).

Run from backend/:  python -m scripts.make_test_audio   (needs ffmpeg on PATH)
Output: tests/fixtures/audio/
"""
import base64
import subprocess
from pathlib import Path

from mutagen.flac import FLAC, Picture
from mutagen.id3 import APIC, ID3, TALB, TCON, TDRC, TIT2, TPE1
from mutagen.mp4 import MP4, MP4Cover
from mutagen.oggvorbis import OggVorbis

OUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "audio"


def ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", *args], check=True)


def tone(path: Path, freq: int, seconds: float, extra: list[str]) -> None:
    ffmpeg("-f", "lavfi", "-i", f"sine=frequency={freq}:duration={seconds}:sample_rate=22050", "-ac", "1", *extra, str(path))


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    cover = OUT / "cover.jpg"
    ffmpeg("-f", "lavfi", "-i", "color=c=0x5c266f:s=64x64", "-frames:v", "1", str(cover))
    art = cover.read_bytes()

    mp3 = OUT / "lilac-hour.mp3"
    tone(mp3, 440, 3, ["-b:a", "48k"])
    id3 = ID3()
    id3.add(TIT2(encoding=3, text="Lilac Hour"))
    id3.add(TPE1(encoding=3, text=["Satin Tone", "Velvet Hum"]))
    id3.add(TALB(encoding=3, text="Test Tones Vol. 1"))
    id3.add(TCON(encoding=3, text="Ambient"))
    id3.add(TDRC(encoding=3, text="2026-03-14"))
    id3.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=art))
    id3.save(mp3)

    m4a = OUT / "amethyst.m4a"
    tone(m4a, 523, 3, ["-c:a", "aac", "-b:a", "48k"])
    mp4 = MP4(m4a)
    mp4["\xa9nam"], mp4["\xa9ART"], mp4["\xa9alb"], mp4["\xa9gen"] = ["Amethyst"], ["Satin Tone"], ["Test Tones Vol. 1"], ["Chillout"]
    mp4["covr"] = [MP4Cover(art, imageformat=MP4Cover.FORMAT_JPEG)]
    mp4.save()

    flac_path = OUT / "violet-sheen.flac"
    tone(flac_path, 392, 3, [])
    flac = FLAC(flac_path)
    flac["title"], flac["artist"], flac["album"], flac["genre"] = "Violet Sheen", "Velvet Hum", "Ribbons", "Classical"
    pic = Picture()
    pic.type, pic.mime, pic.data = 3, "image/jpeg", art
    flac.add_picture(pic)
    flac.save()

    ogg_path = OUT / "midnight.ogg"
    tone(ogg_path, 330, 3, ["-c:a", "libvorbis", "-q:a", "0"])
    ogg = OggVorbis(ogg_path)
    ogg["title"], ogg["artist"], ogg["genre"] = "Midnight", "Satin Tone; Velvet Hum", "Lofi"
    ogg["metadata_block_picture"] = [base64.b64encode(pic.write()).decode()]
    ogg.save()

    # No tags at all: the title and artist must come from the filename.
    tone(OUT / "Plum Choir - Untagged Tone.wav", 262, 2, ["-c:a", "pcm_s16le", "-ar", "8000"])

    # A click every 0.5 s (120 BPM) for the tempo test.
    ffmpeg("-f", "lavfi", "-i",
           "aevalsrc='0.9*sin(2*PI*1000*t)*exp(-60*mod(t\\,0.5))':s=22050:d=8", "-ac", "1", "-b:a", "64k",
           str(OUT / "click-120bpm.mp3"))
    cover.unlink()
    for f in sorted(OUT.iterdir()):
        print(f"{f.name}: {f.stat().st_size} bytes")


if __name__ == "__main__":
    main()
