"""Music providers and the provider-specific side of a song.

A `MusicProvider` row describes an integration (e.g. a licensed streaming
service). A `SongProviderLink` says "this catalogue song is available on that
provider under this id". The catalogue itself never depends on either.
"""
from sqlalchemy import BigInteger, Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class MusicProvider(TimestampMixin, Base):
    __tablename__ = "music_providers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    key: Mapped[str] = mapped_column(String(50), unique=True)  # stable code id, e.g. "mock"
    display_name: Mapped[str] = mapped_column(String(100))
    # False until real credentials/licensing are configured. The UI shows
    # "playback requires configuration" for any provider where this is false.
    is_configured: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    supports_playback: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_mock: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


class SongProviderLink(TimestampMixin, Base):
    __tablename__ = "song_provider_links"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id", ondelete="CASCADE"))
    provider_id: Mapped[int] = mapped_column(ForeignKey("music_providers.id", ondelete="CASCADE"))
    provider_track_id: Mapped[str] = mapped_column(String(200))
    # Deep link / URI handed to the provider's own player. We store references,
    # never audio files.
    playback_uri: Mapped[str | None] = mapped_column(String(1000))
    # Licence the provider publishes for this track (e.g. a Creative Commons URL).
    # We check it BEFORE doing anything beyond streaming, such as analysing audio.
    license_url: Mapped[str | None] = mapped_column(String(500))

    song = relationship("Song", back_populates="provider_links")
    provider: Mapped[MusicProvider] = relationship()

    __table_args__ = (
        UniqueConstraint("provider_id", "provider_track_id", name="uq_song_provider_links_provider_track"),
        UniqueConstraint("song_id", "provider_id", name="uq_song_provider_links_song_provider"),
    )
