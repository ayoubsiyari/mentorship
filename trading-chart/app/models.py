from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, LargeBinary, String, Text, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from typing import Any


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(50), default="user")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    has_journal_access: Mapped[bool] = mapped_column(Boolean, default=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    country: Mapped[str | None] = mapped_column(String(120), nullable=True)
    group_id: Mapped[int | None] = mapped_column(ForeignKey("journal_groups.id"), nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_code: Mapped[str | None] = mapped_column(String(6), nullable=True)
    verification_code_expires: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reset_code: Mapped[str | None] = mapped_column(String(6), nullable=True)
    reset_code_expires: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    user_source: Mapped[str | None] = mapped_column(String(50), nullable=True)  # 'talaria-prop', 'organic', etc.

    sessions: Mapped[list[TradingSession]] = relationship(back_populates="user", cascade="all, delete-orphan")
    journal_profiles: Mapped[list[JournalProfile]] = relationship(back_populates="user", cascade="all, delete-orphan")
    journal_entries: Mapped[list[JournalEntry]] = relationship(back_populates="user", cascade="all, delete-orphan")
    strategies: Mapped[list[Strategy]] = relationship(back_populates="user", cascade="all, delete-orphan")
    group: Mapped[JournalGroup | None] = relationship(back_populates="users")


class TradingSession(Base):
    __tablename__ = "trading_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)

    name: Mapped[str] = mapped_column(String(200))
    session_type: Mapped[str] = mapped_column(String(20))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    start_balance: Mapped[float | None] = mapped_column(Float, nullable=True)
    start_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    symbol: Mapped[str | None] = mapped_column(String(50), nullable=True)

    user: Mapped[User] = relationship(back_populates="sessions")
    trades: Mapped[list[Trade]] = relationship(back_populates="session", cascade="all, delete-orphan")


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("trading_sessions.id"), index=True)

    trade_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    symbol: Mapped[str | None] = mapped_column(String(50), nullable=True)
    side: Mapped[str | None] = mapped_column(String(20), nullable=True)

    entry: Mapped[float | None] = mapped_column(Float, nullable=True)
    exit: Mapped[float | None] = mapped_column(Float, nullable=True)
    pnl: Mapped[float] = mapped_column(Float, default=0.0)

    stop_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    take_profit: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_amount: Mapped[float | None] = mapped_column(Float, nullable=True)

    rr_planned: Mapped[float | None] = mapped_column(Float, nullable=True)
    rr_actual: Mapped[float | None] = mapped_column(Float, nullable=True)
    r_multiple: Mapped[float | None] = mapped_column(Float, nullable=True)

    price_move_pips: Mapped[float | None] = mapped_column(Float, nullable=True)
    quantity: Mapped[float | None] = mapped_column(Float, nullable=True)

    close_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    holding_time_hours: Mapped[float | None] = mapped_column(Float, nullable=True)

    entry_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    exit_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    day_of_week: Mapped[str | None] = mapped_column(String(12), nullable=True)
    month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hour_of_entry: Mapped[int | None] = mapped_column(Integer, nullable=True)
    hour_of_exit: Mapped[int | None] = mapped_column(Integer, nullable=True)

    mfe: Mapped[float | None] = mapped_column(Float, nullable=True)
    mae: Mapped[float | None] = mapped_column(Float, nullable=True)
    highest_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    lowest_price: Mapped[float | None] = mapped_column(Float, nullable=True)

    pre_trade_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    post_trade_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    entry_screenshot: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    entry_screenshot_mime: Mapped[str | None] = mapped_column(String(100), nullable=True)
    exit_screenshot: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    exit_screenshot_mime: Mapped[str | None] = mapped_column(String(100), nullable=True)

    session: Mapped[TradingSession] = relationship(back_populates="trades")


class BootcampRegistration(Base):
    __tablename__ = "bootcamp_registrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(255), index=True)

    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    country: Mapped[str] = mapped_column(String(120))
    age: Mapped[int] = mapped_column(Integer)

    telegram: Mapped[str | None] = mapped_column(String(120), nullable=True)
    discord: Mapped[str] = mapped_column(String(120))
    instagram: Mapped[str | None] = mapped_column(String(120), nullable=True)

    agree_terms: Mapped[bool] = mapped_column(Boolean, default=False)
    agree_rules: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ========== JOURNAL MODELS (from old VPS) ==========

class JournalGroup(Base):
    __tablename__ = "journal_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    users: Mapped[list[User]] = relationship(back_populates="group")


class JournalProfile(Base):
    __tablename__ = "journal_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    mode: Mapped[str] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ftp_host: Mapped[str | None] = mapped_column(String(255), nullable=True)
    ftp_port: Mapped[int | None] = mapped_column(Integer, nullable=True)
    ftp_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ftp_password: Mapped[str | None] = mapped_column(String(255), nullable=True)

    user: Mapped[User] = relationship(back_populates="journal_profiles")
    entries: Mapped[list[JournalEntry]] = relationship(back_populates="profile", cascade="all, delete-orphan")
    import_batches: Mapped[list[ImportBatch]] = relationship(back_populates="profile", cascade="all, delete-orphan")


class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("journal_profiles.id"), index=True)
    symbol: Mapped[str] = mapped_column(String(20))
    direction: Mapped[str] = mapped_column(String(10))
    entry_price: Mapped[float] = mapped_column(Float)
    exit_price: Mapped[float] = mapped_column(Float)
    stop_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    take_profit: Mapped[float | None] = mapped_column(Float, nullable=True)
    high_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    low_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    variables: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    quantity: Mapped[float] = mapped_column(Float)
    contract_size: Mapped[float | None] = mapped_column(Float, nullable=True)
    instrument_type: Mapped[str] = mapped_column(String(20))
    risk_amount: Mapped[float] = mapped_column(Float)
    pnl: Mapped[float] = mapped_column(Float)
    strategy: Mapped[str | None] = mapped_column(String(64), nullable=True)
    setup: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rr: Mapped[float] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    date: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    commission: Mapped[float | None] = mapped_column(Float, nullable=True)
    slippage: Mapped[float | None] = mapped_column(Float, nullable=True)
    open_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    close_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    duration_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entry_screenshot: Mapped[str | None] = mapped_column(String(512), nullable=True)
    exit_screenshot: Mapped[str | None] = mapped_column(String(512), nullable=True)
    import_batch_id: Mapped[int | None] = mapped_column(ForeignKey("import_batches.id"), nullable=True)
    extra_data: Mapped[Any | None] = mapped_column(JSON, nullable=True)

    user: Mapped[User] = relationship(back_populates="journal_entries")
    profile: Mapped[JournalProfile] = relationship(back_populates="entries")
    import_batch: Mapped[ImportBatch | None] = relationship(back_populates="entries")


class Strategy(Base):
    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    entry_rules: Mapped[Any] = mapped_column(JSON)
    exit_rules: Mapped[Any] = mapped_column(JSON)
    risk_management: Mapped[Any] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped[User] = relationship(back_populates="strategies")


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    profile_id: Mapped[int] = mapped_column(ForeignKey("journal_profiles.id"), index=True)
    filename: Mapped[str] = mapped_column(String(256))
    filepath: Mapped[str] = mapped_column(String(512))
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    profile: Mapped[JournalProfile] = relationship(back_populates="import_batches")
    entries: Mapped[list[JournalEntry]] = relationship(back_populates="import_batch")


class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
