"""Each test proves one rule the database itself enforces.

Why test the database and not just the Python code? Application code has bugs
and gets bypassed by scripts; constraints are the last line of defence for
data integrity (and analytics accuracy).
"""
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import (
    Artist, ListeningEvent, Song, SongArtist, SongFeatures, User, UserCollection, UserInteraction,
)

T0 = datetime(2026, 11, 2, 9, 0, tzinfo=timezone.utc)


def make_user(db, email="ada@example.com") -> User:
    u = User(email=email, password_hash="argon2-hash-placeholder", display_name="Ada")
    db.add(u)
    db.flush()
    return u


def make_song(db, title="Song A", artist_name="Artist A") -> Song:
    artist = Artist(name=artist_name, data_source="mock_dev")
    song = Song(title=title, duration_ms=200_000, data_source="mock_dev")
    song.artist_links.append(SongArtist(artist=artist, position=0))
    db.add(song)
    db.flush()
    return song


def event(user, song, start, seconds, listened_s=None) -> ListeningEvent:
    return ListeningEvent(
        user_id=user.id, song_id=song.id, started_at=start,
        ended_at=start + timedelta(seconds=seconds),
        listened_ms=(listened_s if listened_s is not None else seconds) * 1000,
        song_duration_ms=song.duration_ms, play_date=date(2026, 11, 2),
    )


def test_emails_are_unique_case_insensitively(db):
    make_user(db, "Ada@Example.com")
    with pytest.raises(IntegrityError):
        make_user(db, "ada@example.com")


def test_song_cannot_be_in_a_collection_twice(db):
    user, song = make_user(db), make_song(db)
    db.add(UserCollection(user_id=user.id, song_id=song.id))
    db.flush()
    with pytest.raises(IntegrityError):
        db.add(UserCollection(user_id=user.id, song_id=song.id))
        db.flush()


@pytest.mark.parametrize("field,value", [("energy", 1.5), ("valence", -0.1), ("tempo", 5)])
def test_song_features_reject_out_of_range_values(db, field, value):
    song = make_song(db)
    vals = dict(tempo=120, energy=0.5, danceability=0.5, acousticness=0.5, valence=0.5, instrumentalness=0.1)
    vals[field] = value
    with pytest.raises(IntegrityError):
        db.add(SongFeatures(song_id=song.id, feature_source="mock_dev", **vals))
        db.flush()


def test_data_source_must_be_a_known_label(db):
    with pytest.raises(IntegrityError):
        db.add(Artist(name="X", data_source="scraped"))
        db.flush()


def test_listening_events_cannot_overlap_for_same_user(db):
    """Prevents double-counting the same listening time."""
    user, song = make_user(db), make_song(db)
    db.add(event(user, song, T0, 180))
    db.flush()
    with pytest.raises(IntegrityError):
        db.add(event(user, song, T0 + timedelta(seconds=60), 120))  # overlaps the first
        db.flush()


def test_back_to_back_and_other_users_events_are_allowed(db):
    u1, u2, song = make_user(db), make_user(db, "grace@example.com"), make_song(db)
    db.add_all([
        event(u1, song, T0, 180),
        event(u1, song, T0 + timedelta(seconds=180), 100),  # starts exactly when previous ended
        event(u2, song, T0, 180),                            # different user, same time
    ])
    db.flush()  # no error


def test_paused_time_is_excluded_from_listened_ms(db):
    """200s wall-clock span with a 50s pause is stored as 150s listened."""
    user, song = make_user(db), make_song(db)
    ev = event(user, song, T0, 200, listened_s=150)
    db.add(ev)
    db.flush()
    assert ev.listened_ms == 150_000


def test_listened_time_cannot_exceed_wall_clock_span(db):
    user, song = make_user(db), make_song(db)
    with pytest.raises(IntegrityError):
        db.add(event(user, song, T0, 60, listened_s=300))
        db.flush()


def test_interaction_must_target_exactly_one_of_song_or_artist(db):
    user, song = make_user(db), make_song(db)
    artist_id = song.artist_links[0].artist_id
    db.add(UserInteraction(user_id=user.id, song_id=song.id, interaction_type="interested"))
    db.add(UserInteraction(user_id=user.id, artist_id=artist_id, interaction_type="interested"))
    db.flush()
    for bad in (
        UserInteraction(user_id=user.id, interaction_type="interested"),  # neither
        UserInteraction(user_id=user.id, song_id=song.id, artist_id=artist_id, interaction_type="interested"),  # both
    ):
        with pytest.raises(IntegrityError):
            with db.begin_nested():
                db.add(bad)
                db.flush()


def test_a_skip_is_not_stored_as_a_dislike(db):
    """'skipped' is its own neutral type; there is no auto-conversion to 'not_interested'."""
    user, song = make_user(db), make_song(db)
    db.add(UserInteraction(user_id=user.id, song_id=song.id, interaction_type="skipped"))
    db.flush()
    with pytest.raises(IntegrityError):
        db.add(UserInteraction(user_id=user.id, song_id=song.id, interaction_type="disliked"))
        db.flush()


def test_deleting_a_user_deletes_their_history_and_collection(db):
    """Privacy: account deletion leaves no personal listening data behind."""
    user, song = make_user(db), make_song(db)
    db.add(event(user, song, T0, 100))
    db.add(UserCollection(user_id=user.id, song_id=song.id))
    db.flush()
    db.delete(user)
    db.flush()
    assert db.query(ListeningEvent).count() == 0
    assert db.query(UserCollection).count() == 0
    assert db.query(Song).count() == 1  # shared catalogue is untouched
