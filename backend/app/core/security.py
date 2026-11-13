"""Password hashing and session tokens."""
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from app.core.config import get_settings

SESSION_COOKIE = "spotifree_session"
_hasher = PasswordHasher()  # Argon2id with safe defaults; the salt is embedded in each hash
# Verified against when an email doesn't exist, so "unknown email" and "wrong password"
# take the same time and can't be told apart by an attacker.
_DUMMY_HASH = _hasher.hash("not-a-real-password")


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerifyMismatchError, InvalidHashError):
        return False


def create_session_token(user_id: uuid.UUID) -> str:
    now = datetime.now(timezone.utc)
    settings = get_settings()
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def read_session_token(token: str) -> uuid.UUID | None:
    """Return the user id if the token is valid and unexpired, else None."""
    try:
        payload = jwt.decode(token, get_settings().secret_key, algorithms=["HS256"])
        return uuid.UUID(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
