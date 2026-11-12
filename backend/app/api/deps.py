from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import SESSION_COOKIE, read_session_token
from app.models import User


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Authenticate from the httpOnly session cookie."""
    token = request.cookies.get(SESSION_COOKIE)
    user_id = read_session_token(token) if token else None
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user
