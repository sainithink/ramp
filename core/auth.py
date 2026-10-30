"""Registration, login and session handling.

Passwords: bcrypt. bcrypt silently truncates at 72 bytes, so the password is
SHA-256'd and base64'd first — that way a long passphrase keeps its full
entropy instead of only the first 72 characters counting.

Sessions: a signed JWT in an httpOnly cookie. httpOnly keeps it out of reach
of page JavaScript, which matters because the same origin serves user content.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from email_validator import EmailNotValidError, validate_email
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.db import User

log = logging.getLogger(__name__)

COOKIE_NAME = "saira_session"
TOKEN_TTL = timedelta(days=30)
_ALGO = "HS256"

# Reuse the master key for signing when no dedicated secret is set, so there is
# only one secret to manage in deployment.
_SECRET = os.environ.get("SAIRA_JWT_SECRET") or None


def _secret() -> str:
    global _SECRET
    if _SECRET is None:
        from core.crypto import _load_master
        _SECRET = _load_master().decode()
    return _SECRET


# ── Passwords ────────────────────────────────────────────────────────────────

def _prehash(password: str) -> bytes:
    """SHA-256 then base64, so bcrypt's 72-byte cap never truncates a real password."""
    return base64.b64encode(hashlib.sha256(password.encode()).digest())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prehash(password), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_prehash(password), hashed.encode())
    except (ValueError, TypeError):
        return False


# ── Tokens ───────────────────────────────────────────────────────────────────

def make_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {"sub": user_id, "iat": now, "exp": now + TOKEN_TTL, "jti": secrets.token_hex(8)},
        _secret(), algorithm=_ALGO,
    )


def read_claims(token: str) -> dict | None:
    """Return the token's claims, or None if it is missing, invalid or expired."""
    if not token:
        return None
    try:
        return jwt.decode(token, _secret(), algorithms=[_ALGO])
    except jwt.PyJWTError:
        return None


def read_token(token: str) -> str | None:
    """Return the user id, or None if the token is missing, invalid or expired."""
    claims = read_claims(token)
    return claims.get("sub") if claims else None


def token_is_current(claims: dict, user: User) -> bool:
    """False for a session issued before the password was last changed.

    Without this a stolen cookie would keep working after the password was
    changed, which is usually the very reason someone changes it.
    """
    changed = getattr(user, "password_changed_at", None)
    if changed is None:
        return True
    issued = claims.get("iat")
    if issued is None:
        return False
    if changed.tzinfo is None:                       # SQLite hands back naive datetimes
        changed = changed.replace(tzinfo=timezone.utc)
    # A second of slack: `iat` is whole seconds, the column keeps microseconds.
    return datetime.fromtimestamp(issued, timezone.utc) >= changed - timedelta(seconds=1)


# ── Validation ───────────────────────────────────────────────────────────────

MIN_PASSWORD = 8
MAX_WAKE_NAME = 24


def normalise_email(raw: str) -> str:
    """Return a normalised address, or raise ValueError with a usable message."""
    try:
        # Strip first — pasted addresses routinely carry surrounding whitespace,
        # which the validator rejects as an invalid domain character.
        # Deliverability checks need DNS; skip them so registration works offline
        # and does not stall on a slow resolver.
        return validate_email((raw or "").strip(),
                              check_deliverability=False).normalized.lower()
    except EmailNotValidError as exc:
        raise ValueError(str(exc)) from exc


def validate_wake_name(raw: str) -> str:
    """The assistant's name must be speakable and matchable as a single word."""
    name = (raw or "").strip()
    if not name:
        return "Saira"
    if len(name) > MAX_WAKE_NAME:
        raise ValueError(f"Name must be {MAX_WAKE_NAME} characters or fewer.")
    if not name.replace(" ", "").isalpha():
        raise ValueError("Name must contain only letters.")
    if len(name.split()) > 1:
        raise ValueError("Use a single word so it can be detected reliably.")
    if len(name) < 3:
        raise ValueError("Name must be at least 3 letters — shorter names "
                         "trigger on ordinary speech.")
    return name.title()


# ── Operations ───────────────────────────────────────────────────────────────

class AuthError(Exception):
    pass


def register(session: Session, email: str, password: str,
             wake_name: str = "Saira", display_name: str = "") -> User:
    email = normalise_email(email)
    if len(password) < MIN_PASSWORD:
        raise AuthError(f"Password must be at least {MIN_PASSWORD} characters.")
    try:
        wake = validate_wake_name(wake_name)
    except ValueError as exc:
        raise AuthError(str(exc)) from exc

    if session.scalar(select(User).where(User.email == email)):
        raise AuthError("An account with that email already exists.")

    # First account to register becomes the admin — there is no other way to
    # bootstrap one, and it avoids shipping default credentials.
    first = session.scalar(select(func.count()).select_from(User)) == 0

    user = User(
        email=email,
        password_hash=hash_password(password),
        wake_name=wake,
        display_name=(display_name or email.split("@")[0]).strip()[:80],
        role="admin" if first else "user",
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    log.info("Registered %s (%s)", email, user.role)
    return user


def change_password(session: Session, user: User, current: str, new: str) -> None:
    """Replace a user's password, having checked they know the old one."""
    if not verify_password(current, user.password_hash):
        raise AuthError("That is not your current password.")
    if len(new) < MIN_PASSWORD:
        raise AuthError(f"Password must be at least {MIN_PASSWORD} characters.")
    if verify_password(new, user.password_hash):
        raise AuthError("That is already your password.")

    user.password_hash = hash_password(new)
    user.password_changed_at = datetime.now(timezone.utc)
    session.commit()
    log.info("Password changed for %s", user.email)


def authenticate(session: Session, email: str, password: str) -> User:
    try:
        email = normalise_email(email)
    except ValueError:
        raise AuthError("Incorrect email or password.")

    user = session.scalar(select(User).where(User.email == email))
    # Verify even when the user is missing, so response time doesn't reveal
    # whether an address is registered.
    ok = verify_password(password, user.password_hash if user else
                         "$2b$12$" + "." * 53)
    if not user or not ok:
        raise AuthError("Incorrect email or password.")
    if not user.is_active:
        raise AuthError("This account has been disabled.")

    user.last_seen_at = datetime.now(timezone.utc)
    session.commit()
    return user
