"""Picks the configured provider. Returns None when nothing is configured."""
from functools import lru_cache

from app.core.config import get_settings
from app.providers.base import MusicProviderAdapter
from app.providers.jamendo import JamendoAdapter


@lru_cache
def _jamendo(client_id: str) -> JamendoAdapter:
    return JamendoAdapter(client_id)


def get_music_provider() -> MusicProviderAdapter | None:
    """FastAPI dependency. Tests override this with a fake adapter."""
    client_id = get_settings().jamendo_client_id
    return _jamendo(client_id) if client_id else None
