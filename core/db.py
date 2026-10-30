"""Database layer — users, usage, and per-user encrypted blobs.

SQLite via SQLAlchemy. The engine URL is the only thing tying us to SQLite, so
moving to the PostgreSQL already planned for the server is a connection-string
change, not a rewrite. WAL mode is on so reads don't block the writer.
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, String, Text,
    create_engine, event, func, inspect, select, text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, Session

log = logging.getLogger(__name__)

DB_URL = os.environ.get("SAIRA_DB_URL", f"sqlite:///{Path('saira.db').resolve()}")

# Free tier is deliberately generous for now — a real payment model comes later.
# A conversation = one completed user utterance + reply.
PLAN_LIMITS: dict[str, int] = {
    "free": 100,     # conversations per month
    "pro": 5000,
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id:            Mapped[str]  = mapped_column(String(36), primary_key=True,
                                                default=lambda: str(uuid.uuid4()))
    email:         Mapped[str]  = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str]  = mapped_column(String(255))
    display_name:  Mapped[str]  = mapped_column(String(80), default="")

    # What the user calls their assistant. Chosen at registration, editable later.
    wake_name:     Mapped[str]  = mapped_column(String(40), default="Saira")

    role:          Mapped[str]  = mapped_column(String(16), default="user")   # user | admin
    plan:          Mapped[str]  = mapped_column(String(16), default="free")
    # Admin override; when set it wins over PLAN_LIMITS[plan].
    custom_limit:  Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_active:     Mapped[bool] = mapped_column(Boolean, default=True)
    created_at:    Mapped[datetime] = mapped_column(DateTime, default=_now)
    last_seen_at:  Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Set when the password changes. Sessions issued before this are refused,
    # so changing the password actually signs other devices out.
    password_changed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # None until the emailed activation code is entered.
    email_verified_at:   Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    usage: Mapped[list["UsageEvent"]] = relationship(
        back_populates="user", cascade="all, delete-orphan")
    codes: Mapped[list["OtpCode"]] = relationship(
        back_populates="user", cascade="all, delete-orphan")

    @property
    def is_verified(self) -> bool:
        return self.email_verified_at is not None
    blobs: Mapped[list["UserBlob"]] = relationship(
        back_populates="user", cascade="all, delete-orphan")

    @property
    def monthly_limit(self) -> int:
        if self.custom_limit is not None:
            return self.custom_limit
        return PLAN_LIMITS.get(self.plan, PLAN_LIMITS["free"])

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


class UsageEvent(Base):
    """One row per completed conversation. Kept granular so limits can later be
    changed (per day, per minute of audio) without a migration."""
    __tablename__ = "usage_events"

    id:         Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id:    Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind:       Mapped[str] = mapped_column(String(32), default="conversation")
    amount:     Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now, index=True)

    user: Mapped[User] = relationship(back_populates="usage")


class UserBlob(Base):
    """Per-user encrypted payload: memory, preferences or profile.

    Encrypted with a key derived from the server master key and the user id, so
    one leaked blob does not expose the others and nothing is readable from the
    database alone. See core/crypto.py.
    """
    __tablename__ = "user_blobs"

    user_id:    Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"),
                                            primary_key=True)
    kind:       Mapped[str] = mapped_column(String(24), primary_key=True)  # memory|preferences|profile
    payload:    Mapped[str] = mapped_column(Text, default="")              # Fernet token
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    user: Mapped[User] = relationship(back_populates="blobs")


_engine = create_engine(DB_URL, future=True, echo=False,
                        connect_args={"check_same_thread": False}
                        if DB_URL.startswith("sqlite") else {})


@event.listens_for(_engine, "connect")
def _sqlite_pragmas(dbapi_conn, _):
    if not DB_URL.startswith("sqlite"):
        return
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL")    # readers don't block the writer
    cur.execute("PRAGMA foreign_keys=ON")     # off by default in SQLite
    cur.execute("PRAGMA busy_timeout=5000")
    cur.close()


def get_session() -> Session:
    return Session(_engine, future=True)


class OtpCode(Base):
    """A one-time code emailed to a user, for activation or a password reset.

    The code itself is never stored — only an HMAC of it — so a copy of the
    database does not hand someone a working code. Short expiry and an attempt
    cap do the rest of the work, because six digits is a small search space.
    """
    __tablename__ = "otp_codes"

    id:         Mapped[str] = mapped_column(String(36), primary_key=True,
                                            default=lambda: str(uuid.uuid4()))
    user_id:    Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"),
                                            index=True)
    purpose:    Mapped[str] = mapped_column(String(16))        # verify | reset
    code_hash:  Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    attempts:   Mapped[int] = mapped_column(Integer, default=0)

    user: Mapped["User"] = relationship(back_populates="codes")


def _add_missing_columns() -> list[str]:
    """Add nullable columns that exist on the models but not yet in the file.

    There is no migration tool here and create_all() only ever creates whole
    tables, so a column added to a model would be invisible on an existing
    database. Only nullable columns can be handled this way; anything more
    involved needs a real migration.
    """
    added: list[str] = []
    inspector = inspect(_engine)
    with _engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if not inspector.has_table(table.name):
                continue
            existing = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing:
                    continue
                if not column.nullable:
                    log.warning("Column %s.%s is new but not nullable — "
                                "it needs a migration by hand.", table.name, column.name)
                    continue
                type_sql = column.type.compile(_engine.dialect)
                conn.execute(text(
                    f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {type_sql}'))
                added.append(f"{table.name}.{column.name}")
                log.info("Added column %s.%s", table.name, column.name)
    return added


def init_db() -> None:
    Base.metadata.create_all(_engine)
    added = _add_missing_columns()

    # Accounts that predate email verification were never asked to verify, so
    # grandfather them in rather than locking their owners out.
    if "users.email_verified_at" in added:
        with Session(_engine) as s:
            grandfathered = s.query(User).update(
                {User.email_verified_at: _now()}, synchronize_session=False)
            s.commit()
        if grandfathered:
            log.info("Marked %d pre-existing account(s) as verified", grandfathered)


# ── Usage ────────────────────────────────────────────────────────────────────

def _month_start() -> datetime:
    n = _now()
    return n.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def usage_this_month(session: Session, user_id: str) -> int:
    total = session.scalar(
        select(func.coalesce(func.sum(UsageEvent.amount), 0))
        .where(UsageEvent.user_id == user_id,
               UsageEvent.created_at >= _month_start())
    )
    return int(total or 0)


def record_usage(session: Session, user_id: str, kind: str = "conversation",
                 amount: int = 1) -> None:
    session.add(UsageEvent(user_id=user_id, kind=kind, amount=amount))
    session.commit()


def over_limit(session: Session, user: User) -> bool:
    return usage_this_month(session, user.id) >= user.monthly_limit
