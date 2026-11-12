from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.security import SESSION_COOKIE, verify_password
from app.models import User, UserPreferences
from app.schemas.auth import DeleteAccountRequest, PreferencesOut, PreferencesUpdate, ProfileUpdate, UserOut

router = APIRouter(prefix="/profile", tags=["profile"])


@router.patch("", response_model=UserOut)
def update_profile(body: ProfileUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    user.display_name = body.display_name.strip()
    db.commit()
    return user


@router.get("/preferences", response_model=PreferencesOut)
def get_preferences(user: User = Depends(get_current_user)) -> UserPreferences:
    return user.preferences


@router.patch("/preferences", response_model=PreferencesOut)
def update_preferences(
    body: PreferencesUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> UserPreferences:
    prefs = user.preferences
    changes = body.model_dump(exclude_unset=True, exclude_none=True)
    # Validate the combined result BEFORE changing anything.
    short = changes.get("short_term_days", prefs.short_term_days)
    long = changes.get("long_term_days", prefs.long_term_days)
    if long <= short:
        raise HTTPException(422, "long_term_days must be greater than short_term_days")
    if "preferred_genres" in changes:
        cleaned = sorted({
            g.strip().lower() for g in changes["preferred_genres"] if isinstance(g, str) and g.strip()
        })[:20]
        changes["preferred_genres"] = cleaned
    for field, value in changes.items():
        setattr(prefs, field, value)
    db.commit()
    return prefs


@router.delete("", status_code=status.HTTP_204_NO_CONTENT, summary="Permanently delete the account and all its data")
def delete_account(
    body: DeleteAccountRequest, response: Response,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
) -> None:
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Incorrect password")
    db.delete(user)  # cascades to preferences, collection, interactions, listening history
    db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")
