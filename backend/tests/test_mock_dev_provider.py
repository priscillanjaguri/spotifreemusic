from app.core.config import Settings
from app.providers.mock_dev import MockDevAdapter, tone_wav
from tests.conftest import register


def _settings(**overrides) -> Settings:
    base = {"database_url": "postgresql+psycopg://x/y", "secret_key": "k" * 40}
    return Settings(_env_file=None, **{**base, **overrides})  # type: ignore[call-arg]


def test_mock_provider_only_in_development_without_real_provider():
    assert _settings(environment="development", dev_mock_provider=True).mock_provider_enabled
    assert not _settings(environment="production", dev_mock_provider=True).mock_provider_enabled
    assert not _settings(environment="test", dev_mock_provider=True).mock_provider_enabled
    assert not _settings(environment="development", dev_mock_provider=True, jamendo_client_id="abc").mock_provider_enabled
    assert not _settings(environment="development").mock_provider_enabled


def test_mock_search_matches_every_word():
    adapter = MockDevAdapter()
    assert {t.title for t in adapter.search_tracks("lumen lofi")} >= {"Violet Hour", "Morning Chai"}
    assert adapter.search_tracks("no such music anywhere") == []


def test_mock_tracks_are_labelled_mock_dev(client):
    from app.main import app
    from app.providers.registry import get_music_provider

    app.dependency_overrides[get_music_provider] = lambda: MockDevAdapter()
    register(client)
    song = client.get("/api/v1/songs/search?q=violet").json()["results"][0]
    assert song["data_source"] == "mock_dev"
    assert song["playback"]["provider"] == "mock_dev"


def test_tone_is_a_wav_file():
    assert tone_wav("m01", seconds=1).startswith(b"RIFF")
