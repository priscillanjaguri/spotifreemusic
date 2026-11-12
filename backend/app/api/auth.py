from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import SESSION_COOKIE, create_session_token, hash_password, verify_password
from app.models import User, UserPreferences
from app.schemas.auth import LoginRequest, RegisterRequest, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,   # JavaScript cannot read it, so XSS can't steal the session
        samesite="lax",  # not sent on cross-site POSTs (CSRF protection)
        secure=settings.cookie_secure,
        path="/",
    )


def _session_out(user: User, token: str) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        display_name=user.display_name,
        created_at=user.created_at,
        access_token=token,
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, response: Response, db: Session = Depends(get_db)) -> UserOut:
    exists = db.scalar(select(User.id).where(func.lower(User.email) == body.email.lower()))
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    user = User(
        email=body.email, display_name=body.display_name, password_hash=hash_password(body.password),
        preferences=UserPreferences(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_session_token(user.id)
    _set_session_cookie(response, token)
    return _session_out(user, token)


@router.post("/login", response_model=UserOut)
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)) -> UserOut:
    user = db.scalar(select(User).where(func.lower(User.email) == body.email.lower()))
    # Same error and same work whether the email or the password was wrong.
    if not verify_password(body.password, user.password_hash if user else None) or user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    token = create_session_token(user.id)
    _set_session_cookie(response, token)
    return _session_out(user, token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, path="/")


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user
