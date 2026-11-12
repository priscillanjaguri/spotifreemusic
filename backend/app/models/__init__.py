"""Import every model so Alembic and SQLAlchemy see the full metadata."""
from app.models.base import Base
from app.models.catalog import Album, Artist, Genre, Song, SongArtist, SongFeatures, SongGenre
from app.models.collection import UserCollection
from app.models.interactions import UserInteraction
from app.models.library import LibraryUpload
from app.models.listening import ListeningEvent, PlaybackSession
from app.models.providers import MusicProvider, SongProviderLink
from app.models.user import User, UserPreferences

__all__ = [
    "Base", "Album", "Artist", "Genre", "Song", "SongArtist", "SongFeatures", "SongGenre",
    "UserCollection", "UserInteraction", "LibraryUpload", "ListeningEvent", "PlaybackSession",
    "MusicProvider", "SongProviderLink", "User", "UserPreferences",
]
