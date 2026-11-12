"""Provider-independent music catalogue.

Design rule: *metadata* (what a song IS) lives here and never mentions a
streaming provider. *Playback* (how to play it somewhere) lives in
`providers.py`. That split lets us add or swap providers without touching
the catalogue, analytics or recommender.
"""
from datetime import date

from sqlalchemy import (
    BigInteger, CheckConstraint, Date, Float, ForeignKey, Index, Integer, String, Boolean, func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

# Where a row came from. 'mock_dev' rows are fake development data and must be
# labelled as such in the UI -- we never present them as real catalogue content.
DATA_SOURCES = ("mock_dev", "provider", "user_provided")


class Artist(TimestampMixin, Base):
    __tablename__ = "artists"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(300))
    image_url: Mapped[str | None] = mapped_column(String(1000))
    data_source: Mapped[str] = mapped_column(String(20), default="user_provided")

    __table_args__ = (
        CheckConstraint(f"data_source IN {DATA_SOURCES}", name="data_source_valid"),
        Index("ix_artists_name_lower", func.lower(name)),
    )


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)


class Album(TimestampMixin, Base):
    __tablename__ = "albums"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    primary_artist_id: Mapped[int] = mapped_column(
        ForeignKey("artists.id", ondelete="RESTRICT"), index=True
    )
    release_date: Mapped[date | None] = mapped_column(Date)
    cover_url: Mapped[str | None] = mapped_column(String(1000))
    data_source: Mapped[str] = mapped_column(String(20), default="user_provided")

    primary_artist: Mapped[Artist] = relationship()

    __table_args__ = (CheckConstraint(f"data_source IN {DATA_SOURCES}", name="data_source_valid"),)


class Song(TimestampMixin, Base):
    __tablename__ = "songs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    album_id: Mapped[int | None] = mapped_column(
        ForeignKey("albums.id", ondelete="SET NULL"), index=True
    )
    duration_ms: Mapped[int] = mapped_column(Integer)
    explicit: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    isrc: Mapped[str | None] = mapped_column(String(12), unique=True)  # international recording id
    cover_url: Mapped[str | None] = mapped_column(String(1000))
    data_source: Mapped[str] = mapped_column(String(20), default="user_provided")

    album: Mapped[Album | None] = relationship()
    artist_links: Mapped[list["SongArtist"]] = relationship(
        back_populates="song", order_by="SongArtist.position", cascade="all, delete-orphan"
    )
    genres: Mapped[list[Genre]] = relationship(secondary="song_genres")
    provider_links: Mapped[list["SongProviderLink"]] = relationship(
        back_populates="song", cascade="all, delete-orphan"
    )
    features: Mapped["SongFeatures | None"] = relationship(
        back_populates="song", uselist=False, cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint("duration_ms > 0", name="duration_positive"),
        CheckConstraint(f"data_source IN {DATA_SOURCES}", name="data_source_valid"),
        Index("ix_songs_title_lower", func.lower(title)),
    )


class SongArtist(Base):
    """Many-to-many: a song can have several artists (features/collabs).

    Without this table, 'Future & Rihanna' would credit only one of them and
    'top artists' analytics would be wrong.
    """

    __tablename__ = "song_artists"

    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id", ondelete="CASCADE"), primary_key=True)
    artist_id: Mapped[int] = mapped_column(
        ForeignKey("artists.id", ondelete="RESTRICT"), primary_key=True, index=True
    )
    position: Mapped[int] = mapped_column(Integer, default=0)  # 0 = primary artist

    song: Mapped[Song] = relationship(back_populates="artist_links")
    artist: Mapped[Artist] = relationship()


class SongGenre(Base):
    __tablename__ = "song_genres"

    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id", ondelete="CASCADE"), primary_key=True)
    genre_id: Mapped[int] = mapped_column(
        ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True, index=True
    )


class SongFeatures(Base):
    """Numeric audio characteristics used by the content-based recommender.

    Kept in its own table because (a) not every song has features, and (b) the
    *source* of the numbers matters legally and scientifically. We never assume
    that access to a provider's catalogue grants the right to analyse its audio.
    """

    __tablename__ = "song_features"

    song_id: Mapped[int] = mapped_column(ForeignKey("songs.id", ondelete="CASCADE"), primary_key=True)
    tempo: Mapped[float] = mapped_column(Float)  # BPM
    energy: Mapped[float] = mapped_column(Float)  # 0..1
    danceability: Mapped[float] = mapped_column(Float)
    acousticness: Mapped[float] = mapped_column(Float)
    valence: Mapped[float] = mapped_column(Float)  # musical positiveness
    instrumentalness: Mapped[float] = mapped_column(Float)
    feature_source: Mapped[str] = mapped_column(String(20), default="user_provided")

    song: Mapped[Song] = relationship(back_populates="features")

    __table_args__ = (
        CheckConstraint("tempo BETWEEN 30 AND 300", name="tempo_range"),
        CheckConstraint(
            "energy BETWEEN 0 AND 1 AND danceability BETWEEN 0 AND 1 AND acousticness BETWEEN 0 AND 1"
            " AND valence BETWEEN 0 AND 1 AND instrumentalness BETWEEN 0 AND 1",
            name="unit_interval",
        ),
        CheckConstraint(f"feature_source IN {DATA_SOURCES}", name="feature_source_valid"),
    )
