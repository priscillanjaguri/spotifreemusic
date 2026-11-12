"""My Library: music files the user owns and uploaded, played from our own storage.

It is a provider like Jamendo as far as the catalogue is concerned (songs get a
`song_provider_links` row whose playback URI is our authenticated stream endpoint),
but it is never searched: songs come in through uploads only, and are private to the
uploader (`songs.owner_user_id`).
"""
from app.providers.base import MusicProviderAdapter, ProviderTrack


class MyLibraryAdapter(MusicProviderAdapter):
    key = "my_library"
    display_name = "My Library"
    supports_playback = True
    data_source = "user_provided"

    def search_tracks(self, query: str, limit: int = 20) -> list[ProviderTrack]:
        return []

    @staticmethod
    def stream_path(upload_id: int) -> str:
        return f"/api/v1/library/{upload_id}/stream"

    @staticmethod
    def cover_path(upload_id: int) -> str:
        return f"/api/v1/library/{upload_id}/cover"
