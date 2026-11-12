import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=10, max_length=128)
    display_name: str = Field(min_length=1, max_length=100)

    @field_validator("display_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("display_name must not be blank")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    email: EmailStr
    display_name: str
    created_at: datetime


class ProfileUpdate(BaseModel):
    display_name: str = Field(min_length=1, max_length=100)


class PreferencesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    timezone: str
    week_starts_on: int
    record_listening_history: bool
    short_term_days: int
    long_term_days: int


class PreferencesUpdate(BaseModel):
    """All fields optional: send only what you want to change."""
    timezone: str | None = None
    week_starts_on: int | None = Field(default=None, ge=0, le=6)
    record_listening_history: bool | None = None
    short_term_days: int | None = Field(default=None, ge=1, le=365)
    long_term_days: int | None = Field(default=None, ge=2, le=3650)

    @field_validator("timezone")
    @classmethod
    def valid_timezone(cls, v: str | None) -> str | None:
        if v is not None:
            try:
                ZoneInfo(v)
            except Exception:
                raise ValueError("unknown IANA timezone, e.g. 'Africa/Nairobi'")
        return v


class DeleteAccountRequest(BaseModel):
    password: str = Field(max_length=128)
