"""Picks configured catalogue providers. Returns empty / None when nothing is set."""
from functools import lru_cache

from app.core.config import get_settings
from app.providers.audius import AudiusAdapter
from app.providers.base import MusicProviderAdapter
from app.providers.jamendo import JamendoAdapter
from app.providers.mock_dev import MockDevAdapter


@lru_cache
def _jamendo(client_id: str) -> JamendoAdapter:
    return JamendoAdapter(client_id)


@lru_cache
def _audius(host: str, app_name: str, api_key: str | None) -> AudiusAdapter:
    return AudiusAdapter(api_host=host, app_name=app_name, api_key=api_key)


def get_music_providers() -> list[MusicProviderAdapter]:
    """All configured Discover/search providers (Jamendo and/or Audius, else mock)."""
    settings = get_settings()
    providers: list[MusicProviderAdapter] = []
    if settings.jamendo_client_id:
        providers.append(_jamendo(settings.jamendo_client_id))
    if settings.audius_configured:
        providers.append(
            _audius(settings.audius_api_host, settings.audius_app_name, settings.audius_api_key)
        )
    if not providers and settings.mock_provider_enabled:
        providers.append(MockDevAdapter())
    return providers


def get_music_provider() -> MusicProviderAdapter | None:
    """FastAPI dependency for single-provider call sites (recommender seed fallback).

    Prefer `get_music_providers` when search/fan-out matters. Returns the first
    configured catalogue adapter, or None.
    """
    providers = get_music_providers()
    return providers[0] if providers else None
