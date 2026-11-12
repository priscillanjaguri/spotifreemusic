from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import SESSION_COOKIE, read_session_token
from app.models import User


def _token_from_request(request: Request) -> str | None:
    """Prefer Bearer, then ?access_token= (for <audio>/<img>), then the session cookie."""
    auth = request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        value = auth[7:].strip()
        if value:
            return value
    query_token = request.query_params.get("access_token")
    if query_token:
        return query_token
    return request.cookies.get(SESSION_COOKIE)


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Authenticate from Bearer header, access_token query, or httpOnly session cookie."""
    token = _token_from_request(request)
    user_id = read_session_token(token) if token else None
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
