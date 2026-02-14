from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserPublic(BaseModel):
    id: int
    name: str
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime | None = None
    phone: str | None = None
    country: str | None = None
    email_verified: bool = False
    has_journal_access: bool = False
    user_source: str | None = None


class VerifyEmailIn(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)


class ResendCodeIn(BaseModel):
    email: EmailStr


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)
    new_password: str = Field(min_length=8, max_length=128)


class SignupIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    phone: str | None = Field(default=None, max_length=50)
    country: str | None = Field(default=None, max_length=120)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UpdateProfileIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=50)
    country: str | None = Field(default=None, max_length=120)


class SessionPublic(BaseModel):
    id: int
    name: str
    session_type: str
    created_at: datetime | None = None
    start_balance: float | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    symbol: str | None = None


class SessionCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    session_type: str
    start_balance: float | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    symbol: str | None = None


class BootcampRegisterIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=50)
    country: str = Field(min_length=1, max_length=120)
    age: int = Field(ge=0, le=130)
    telegram: str | None = Field(default=None, max_length=120)
    discord: str = Field(min_length=1, max_length=120)
    instagram: str | None = Field(default=None, max_length=120)
    agree_terms: bool
    agree_rules: bool
