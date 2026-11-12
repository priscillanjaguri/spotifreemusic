"""My Library: upload, tagging, dedupe, privacy, streaming (incl. Range), delete, analysis, storage."""
from contextlib import nullcontext
from pathlib import Path

import pytest

from app.analysis import audio_features
from app.services import audio_tags
from tests.conftest import register

AUDIO = Path(__file__).parent / "fixtures" / "audio"
PASSWORD = "correct-horse-battery"


@pytest.fixture()
def settings():
    from app.core.config import get_settings

    return get_settings().model_copy(update={"library_analysis_enabled": False})


@pytest.fixture()
def storage(tmp_path):
    from app.storage.local import LocalFilesystemStorage

    return LocalFilesystemStorage(tmp_path / "library")


@pytest.fixture()
def lib(client, db, storage, settings):
    from app.api.library import get_session_factory
    from app.core.config import get_settings
    from app.main import app
    from app.storage import get_storage

    app.dependency_overrides[get_storage] = lambda: storage
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_session_factory] = lambda: (lambda: nullcontext(db))
    register(client)
    return client


def upload(client, *names, raw=None):
    files = [("files", (n, (AUDIO / n).read_bytes())) for n in names]
    files += [("files", r) for r in raw or []]
    res = client.post("/api/v1/library/uploads", files=files)
    assert res.status_code == 200, res.text
    return res.json()["results"]


def switch_user(client, email):
    client.cookies.clear()
    if register(client, email=email).status_code != 201:
        client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})


# ---- upload + tagging --------------------------------------------------------

def test_upload_requires_login(client):
    assert client.post("/api/v1/library/uploads", files=[("files", ("a.mp3", b"x"))]).status_code == 401
    assert client.get("/api/v1/library").status_code == 401


def test_uploads_every_format_and_reads_tags(lib):
    results = upload(lib, "lilac-hour.mp3", "amethyst.m4a", "violet-sheen.flac", "midnight.ogg", "Plum Choir - Untagged Tone.wav")
    assert [r["status"] for r in results] == ["added"] * 5
    songs = {r["filename"]: r["upload"]["song"] for r in results}

    mp3 = songs["lilac-hour.mp3"]
    assert mp3["title"] == "Lilac Hour" and [a["name"] for a in mp3["artists"]] == ["Satin Tone", "Velvet Hum"]
    assert mp3["album"]["title"] == "Test Tones Vol. 1" and mp3["genres"] == ["ambient"]
    assert 2900 <= mp3["duration_ms"] <= 3200 and mp3["data_source"] == "user_provided"
    upload_id = results[0]["upload"]["id"]
    assert mp3["playback"] == {"provider": "my_library", "stream_url": f"/api/v1/library/{upload_id}/stream", "license_url": None}
    assert mp3["cover_url"] == f"/api/v1/library/{upload_id}/cover"

    assert songs["amethyst.m4a"]["title"] == "Amethyst" and songs["amethyst.m4a"]["genres"] == ["chillout"]
    assert songs["violet-sheen.flac"]["album"]["title"] == "Ribbons"
    assert [a["name"] for a in songs["midnight.ogg"]["artists"]] == ["Satin Tone", "Velvet Hum"]
    assert all(songs[n]["cover_url"] for n in ("amethyst.m4a", "violet-sheen.flac", "midnight.ogg"))

    wav = results[4]
    assert wav["upload"]["song"]["title"] == "Untagged Tone"
    assert [a["name"] for a in wav["upload"]["song"]["artists"]] == ["Plum Choir"]
    assert "filename" in wav["message"] and wav["upload"]["song"]["cover_url"] is None

    # Uploaded songs land in the collection, and the library lists them newest first.
    collection = lib.get("/api/v1/collection").json()
    assert collection["total"] == 5 and {i["source"] for i in collection["items"]} == {"upload"}
    page = lib.get("/api/v1/library").json()
    assert page["total"] == 5 and page["items"][0]["original_filename"] == "Plum Choir - Untagged Tone.wav"
    assert page["limits"]["storage_backend"] == "local" and ".flac" in page["limits"]["accepted_extensions"]


def test_rejects_wrong_type_fake_content_empty_and_oversized(lib, settings):
    settings.library_max_file_mb = 1
    results = upload(lib, raw=[
        ("notes.txt", b"hello"),
        ("song.mp3", b"<html>definitely not audio</html>" * 10),
        ("empty.flac", b""),
        ("huge.wav", b"RIFF\x00\x00\x00\x00WAVE" + b"\x00" * (1024 * 1024 + 10)),
        ("disguised.mp3", (AUDIO / "violet-sheen.flac").read_bytes()),
    ])
    assert [r["status"] for r in results] == ["rejected"] * 5
    assert "Unsupported" in results[0]["message"] and "real MP3" in results[1]["message"]
    assert "empty" in results[2]["message"] and "larger than 1 MB" in results[3]["message"]
    assert lib.get("/api/v1/library").json()["total"] == 0


def test_too_many_files_in_one_request(lib, settings):
    settings.library_max_files_per_request = 2
    files = [("files", (f"{i}.mp3", b"x")) for i in range(3)]
    assert lib.post("/api/v1/library/uploads", files=files).status_code == 413


# ---- dedupe ------------------------------------------------------------------

def test_same_file_twice_is_a_duplicate_per_user(lib, storage):
    first = upload(lib, "lilac-hour.mp3")[0]
    again = upload(lib, "lilac-hour.mp3", raw=[("renamed copy.mp3", (AUDIO / "lilac-hour.mp3").read_bytes())])
    assert [r["status"] for r in again] == ["duplicate", "duplicate"]
    assert again[1]["upload"]["id"] == first["upload"]["id"]
    assert lib.get("/api/v1/library").json()["total"] == 1
    assert len(list(storage.root.rglob("*.mp3"))) == 1

    # Removed from the collection, then re-uploaded: it comes back instead of being silently ignored.
    song_id = first["upload"]["song"]["id"]
    assert lib.delete(f"/api/v1/collection/{song_id}").status_code == 204
    back = upload(lib, "lilac-hour.mp3")[0]
    assert back["status"] == "duplicate" and "added back" in back["message"]
    assert lib.get("/api/v1/collection").json()["total"] == 1

    # Another user uploading the same bytes gets their own private copy.
    switch_user(lib, "grace@example.com")
    other = upload(lib, "lilac-hour.mp3")[0]
    assert other["status"] == "added" and other["upload"]["song"]["id"] != song_id


# ---- privacy + streaming -----------------------------------------------------

def test_only_the_owner_can_stream_see_or_collect(lib):
    item = upload(lib, "lilac-hour.mp3")[0]["upload"]
    song_id, stream_url = item["song"]["id"], item["song"]["playback"]["stream_url"]
    assert lib.get(stream_url).status_code == 200

    switch_user(lib, "mallory@example.com")
    assert lib.get(stream_url).status_code == 404
    assert lib.get(f"/api/v1/library/{item['id']}/cover").status_code == 404
    assert lib.get(f"/api/v1/library/{item['id']}").status_code == 404
    assert lib.delete(f"/api/v1/library/{item['id']}").status_code == 404
    assert lib.get(f"/api/v1/songs/{song_id}").status_code == 404
    assert lib.post("/api/v1/collection", json={"song_id": song_id}).status_code == 404

    lib.cookies.clear()
    assert lib.get(stream_url).status_code == 401


def test_stream_supports_range_requests(lib):
    item = upload(lib, "lilac-hour.mp3")[0]["upload"]
    url, size = item["song"]["playback"]["stream_url"], item["size_bytes"]
    data = (AUDIO / "lilac-hour.mp3").read_bytes()

    full = lib.get(url)
    assert full.status_code == 200 and full.content == data
    assert full.headers["content-type"] == "audio/mpeg" and full.headers["accept-ranges"] == "bytes"

    part = lib.get(url, headers={"Range": "bytes=0-99"})
    assert part.status_code == 206 and part.content == data[:100]
    assert part.headers["content-range"] == f"bytes 0-99/{size}" and part.headers["content-length"] == "100"

    tail = lib.get(url, headers={"Range": "bytes=-50"})
    assert tail.status_code == 206 and tail.content == data[-50:]
    open_ended = lib.get(url, headers={"Range": f"bytes={size - 10}-"})
    assert open_ended.status_code == 206 and open_ended.content == data[-10:]

    assert lib.get(url, headers={"Range": f"bytes={size + 100}-{size + 200}"}).status_code == 416


def test_cover_art_is_served_and_missing_cover_is_404(lib):
    tagged, untagged = upload(lib, "lilac-hour.mp3", "Plum Choir - Untagged Tone.wav")
    res = lib.get(tagged["upload"]["song"]["cover_url"])
    assert res.status_code == 200 and res.headers["content-type"] == "image/jpeg" and res.content[:3] == b"\xff\xd8\xff"
    assert lib.get(f"/api/v1/library/{untagged['upload']['id']}/cover").status_code == 404


# ---- delete ------------------------------------------------------------------

def test_delete_removes_files_song_and_unused_catalogue_rows(lib, storage, db):
    from app.models import Album, Artist, Song

    item = upload(lib, "violet-sheen.flac")[0]["upload"]
    song_id, album_id = item["song"]["id"], item["song"]["album"]["id"]
    artist_id = item["song"]["artists"][0]["id"]
    assert len(list(storage.root.rglob("*"))) > 0

    assert lib.delete(f"/api/v1/library/{item['id']}").status_code == 204
    assert [p for p in storage.root.rglob("*") if p.is_file()] == []
    db.expire_all()
    assert db.get(Song, song_id) is None and db.get(Album, album_id) is None and db.get(Artist, artist_id) is None
    assert lib.get("/api/v1/collection").json()["total"] == 0
    assert lib.delete(f"/api/v1/library/{item['id']}").status_code == 404
    # The same file can be uploaded again afterwards.
    assert upload(lib, "violet-sheen.flac")[0]["status"] == "added"


def test_delete_keeps_artists_still_used_elsewhere(lib, db):
    from app.models import Artist

    mp3, ogg = upload(lib, "lilac-hour.mp3", "midnight.ogg")  # both credit Satin Tone and Velvet Hum
    shared = mp3["upload"]["song"]["artists"][0]["id"]
    assert lib.delete(f"/api/v1/library/{mp3['upload']['id']}").status_code == 204
    db.expire_all()
    assert db.get(Artist, shared) is not None
    assert lib.get("/api/v1/library").json()["total"] == 1


# ---- analysis ----------------------------------------------------------------

@pytest.mark.skipif(not audio_features.librosa_available(), reason="librosa not installed")
def test_upload_queues_analysis_and_stores_features(lib, settings, db):
    from app.models import SongFeatures

    settings.library_analysis_enabled = True
    item = upload(lib, "click-120bpm.mp3")[0]["upload"]
    assert item["analysis_status"] == "pending"  # the response is sent before the job runs

    done = lib.get(f"/api/v1/library/{item['id']}").json()
    assert done["analysis_status"] == "done", done["analysis_error"]
    assert 110 <= done["features"]["tempo"] <= 130
    assert 0 < done["features"]["energy"] <= 1 and done["features"]["analyzer"].startswith("librosa-")
    row = db.get(SongFeatures, item["song"]["id"])
    assert row.feature_source == "user_provided" and row.spectral_centroid_hz > 0 and row.danceability is None


def test_analysis_reports_unavailable_without_librosa(lib, settings, monkeypatch):
    from app.services import library

    settings.library_analysis_enabled = True
    monkeypatch.setattr(library, "librosa_available", lambda: False)
    item = upload(lib, "lilac-hour.mp3")[0]["upload"]
    assert lib.get(f"/api/v1/library/{item['id']}").json()["analysis_status"] == "unavailable"


# ---- pure helpers --------------------------------------------------------------

@pytest.mark.parametrize("head, fmt", [
    (b"ID3\x04\x00", "mp3"), (b"\xff\xfb\x90\x00", "mp3"), (b"\xff\xf1\x50\x80", "aac"),
    (b"\x00\x00\x00\x20ftypM4A ", "m4a"), (b"fLaC\x00", "flac"), (b"OggS\x00", "ogg"),
    (b"RIFF\x10\x00\x00\x00WAVEfmt ", "wav"), (b"<html>", None), (b"", None),
])
def test_sniff_format(head, fmt):
    assert audio_tags.sniff_format(head) == fmt


@pytest.mark.parametrize("stem, title, artists", [
    ("Plum Choir - Untagged Tone", "Untagged Tone", ["Plum Choir"]),
    ("03 Night_Walk", "Night Walk", [audio_tags.UNKNOWN_ARTIST]),
    ("just a title", "just a title", [audio_tags.UNKNOWN_ARTIST]),
])
def test_filename_fallback(stem, title, artists):
    assert audio_tags._from_filename(stem) == (title, artists)


def test_key_estimate_and_energy_scale():
    import numpy as np

    a_minor = np.roll(audio_features._MINOR, 9)
    assert audio_features.estimate_key(a_minor)[:2] == (9, 0)
    assert audio_features.estimate_key(np.zeros(12)) == (None, None, None)
    assert audio_features.energy_from_rms(1.0) == 1.0 and audio_features.energy_from_rms(0.0) == 0.0
    assert 0.4 < audio_features.energy_from_rms(0.05) < 0.6


# ---- storage backends ------------------------------------------------------------

def test_local_storage_refuses_keys_outside_its_root(storage):
    from app.storage import StorageError

    with pytest.raises(StorageError):
        storage.local_path("../../etc/passwd")


def _r2(client=None):
    from app.storage.r2 import R2Storage

    return R2Storage("acct123", "AKIDEXAMPLE", "secret-example", "tunewise-music", client=client)


def test_r2_presigned_url_is_short_lived_and_scoped():
    url = _r2().presigned_url("users/u/1-abc.mp3", "audio/mpeg", 600)
    assert url.startswith("https://acct123.r2.cloudflarestorage.com/tunewise-music/users/u/1-abc.mp3?")
    assert "X-Amz-Expires=600" in url and "response-content-type=audio%2Fmpeg" in url


def test_r2_put_and_delete_use_the_bucket(tmp_path):
    from botocore.stub import ANY, Stubber

    r2 = _r2()
    src = tmp_path / "a.mp3"
    src.write_bytes(b"ID3data")
    with Stubber(r2.client) as stub:
        stub.add_response("put_object", {}, {"Bucket": "tunewise-music", "Key": "k.mp3", "Body": ANY, "ContentType": "audio/mpeg"})
        stub.add_response("delete_object", {}, {"Bucket": "tunewise-music", "Key": "k.mp3"})
        r2.put_file("k.mp3", src, "audio/mpeg")
        r2.delete("k.mp3")
        stub.assert_no_pending_responses()


def test_r2_selected_only_when_fully_configured(monkeypatch):
    from app.core.config import get_settings
    from app.storage import factory

    base = get_settings()
    monkeypatch.setattr(factory, "get_settings", lambda: base.model_copy(update={"r2_account_id": "a", "r2_access_key_id": "b"}))
    assert factory.get_storage().key == "local"
    full = {"r2_account_id": "a", "r2_access_key_id": "b", "r2_secret_access_key": "c", "r2_bucket": "d"}
    monkeypatch.setattr(factory, "get_settings", lambda: base.model_copy(update=full))
    assert factory.get_storage().key == "r2"


def test_stream_redirects_to_presigned_url_on_r2(lib, db, storage):
    from app.main import app
    from app.storage import get_storage

    item = upload(lib, "lilac-hour.mp3")[0]["upload"]

    class FakeR2(type(storage)):
        key = "r2"

        def local_path(self, object_key):
            return None

        def presigned_url(self, object_key, content_type, expires_seconds):
            return f"https://r2.example/{object_key}?expires={expires_seconds}"

    from app.models import LibraryUpload

    db.get(LibraryUpload, item["id"]).storage_backend = "r2"
    db.flush()
    app.dependency_overrides[get_storage] = lambda: FakeR2(storage.root)
    res = lib.get(item["song"]["playback"]["stream_url"], follow_redirects=False)
    assert res.status_code == 307 and res.headers["location"].startswith("https://r2.example/users/")
    assert res.headers["cache-control"] == "no-store"


@pytest.mark.skipif(not audio_features.librosa_available(), reason="librosa not installed")
@pytest.mark.parametrize("name, key_name", [("amethyst.m4a", "C"), ("lilac-hour.mp3", "A"), ("violet-sheen.flac", "G")])
def test_analysis_decodes_every_format_and_finds_the_tone(name, key_name):
    f = audio_features.analyze_file(AUDIO / name)
    assert audio_features.PITCH_CLASSES[f.key] == key_name and f.tempo is None  # a pure tone has no beat
