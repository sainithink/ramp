"""One-time codes for activating an account and resetting a password.

Six digits is a small search space, so the code alone is not the defence:
it expires in ten minutes, dies after five wrong guesses, can only be used
once, and a user can only be sent so many. What is stored is an HMAC of the
code, keyed by the server's master key, so a stolen database yields nothing
that can be typed into the form.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from core import mailer
from core.db import OtpCode, User

log = logging.getLogger(__name__)

VERIFY = "verify"
RESET = "reset"

CODE_DIGITS = 6
TTL = timedelta(minutes=10)
MAX_ATTEMPTS = 5
RESEND_COOLDOWN = timedelta(seconds=60)
MAX_PER_HOUR = 5


class OtpError(Exception):
    """Raised with a message meant to be shown to the person."""


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime | None) -> datetime | None:
    """SQLite gives back naive datetimes; compare them as UTC."""
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _hash(user_id: str, purpose: str, code: str) -> str:
    from core.crypto import _load_master
    return hmac.new(_load_master(),
                    f"{user_id}:{purpose}:{code}".encode(),
                    hashlib.sha256).hexdigest()


def _generate() -> str:
    return f"{secrets.randbelow(10 ** CODE_DIGITS):0{CODE_DIGITS}d}"


def issue(session: Session, user: User, purpose: str) -> str:
    """Create a code for this user, returning it in the clear to be emailed."""
    now = _now()

    recent = session.scalar(
        select(func.count()).select_from(OtpCode)
        .where(OtpCode.user_id == user.id, OtpCode.purpose == purpose,
               OtpCode.created_at >= now - timedelta(hours=1)))
    if (recent or 0) >= MAX_PER_HOUR:
        raise OtpError("Too many codes requested. Try again in an hour.")

    last = session.scalar(
        select(OtpCode)
        .where(OtpCode.user_id == user.id, OtpCode.purpose == purpose)
        .order_by(desc(OtpCode.created_at)).limit(1))
    if last:
        age = now - (_aware(last.created_at) or now)
        if age < RESEND_COOLDOWN:
            wait = int((RESEND_COOLDOWN - age).total_seconds()) or 1
            raise OtpError(f"A code was just sent. Wait {wait} seconds before asking for another.")

    # Only the newest code should work, or an old email stays usable.
    for stale in session.scalars(
        select(OtpCode).where(OtpCode.user_id == user.id, OtpCode.purpose == purpose,
                              OtpCode.consumed_at.is_(None))).all():
        stale.consumed_at = now

    code = _generate()
    session.add(OtpCode(
        user_id=user.id, purpose=purpose,
        code_hash=_hash(user.id, purpose, code),
        expires_at=now + TTL,
    ))
    session.commit()
    return code


def verify(session: Session, user: User, purpose: str, code: str) -> None:
    """Consume a code, or raise OtpError explaining why it was refused."""
    now = _now()
    entry = session.scalar(
        select(OtpCode)
        .where(OtpCode.user_id == user.id, OtpCode.purpose == purpose,
               OtpCode.consumed_at.is_(None))
        .order_by(desc(OtpCode.created_at)).limit(1))

    if entry is None:
        raise OtpError("That code is not valid. Ask for a new one.")
    if (_aware(entry.expires_at) or now) < now:
        raise OtpError("That code has expired. Ask for a new one.")
    if entry.attempts >= MAX_ATTEMPTS:
        entry.consumed_at = now
        session.commit()
        raise OtpError("Too many wrong attempts. Ask for a new code.")

    supplied = (code or "").strip().replace(" ", "")
    if not hmac.compare_digest(entry.code_hash, _hash(user.id, purpose, supplied)):
        entry.attempts += 1
        left = MAX_ATTEMPTS - entry.attempts
        session.commit()
        if left <= 0:
            raise OtpError("Too many wrong attempts. Ask for a new code.")
        raise OtpError(f"That code is not right. {left} attempt{'s' if left != 1 else ''} left.")

    entry.consumed_at = now
    session.commit()


# ── Email bodies ─────────────────────────────────────────────────────────────

def _wrap(title: str, lead: str, code: str, footer: str) -> str:
    return f"""\
<!doctype html>
<html><body style="margin:0;background:#0b0f0d;font-family:-apple-system,Segoe UI,Roboto,sans-serif">
  <div style="max-width:440px;margin:0 auto;padding:40px 24px;color:#e8f0ec">
    <div style="font-size:13px;letter-spacing:.3em;color:#00e676;font-weight:700">S.A.I.R.A</div>
    <h1 style="font-size:20px;margin:24px 0 8px">{title}</h1>
    <p style="font-size:14px;line-height:1.6;color:#9fb3a9;margin:0 0 24px">{lead}</p>
    <div style="font-size:32px;letter-spacing:.3em;font-weight:700;color:#00e676;
                background:rgba(0,230,118,.07);border:1px solid rgba(0,230,118,.25);
                border-radius:10px;padding:18px;text-align:center">{code}</div>
    <p style="font-size:12px;line-height:1.6;color:#6f8379;margin:24px 0 0">{footer}</p>
  </div>
</body></html>"""


async def send_code(email: str, wake_name: str, purpose: str, code: str) -> bool:
    """Takes plain values, not a User: committing expires the ORM instance and
    reading it back after the session closed raises DetachedInstanceError."""
    minutes = int(TTL.total_seconds() // 60)
    if purpose == VERIFY:
        subject = f"{code} is your Saira activation code"
        title = "Activate your account"
        lead = ("Enter this code to finish setting up your account and start "
                f"talking to {wake_name}.")
    else:
        subject = f"{code} is your Saira password reset code"
        title = "Reset your password"
        lead = "Enter this code to choose a new password."

    footer = (f"The code expires in {minutes} minutes and can only be used once. "
              "If you did not ask for it, you can ignore this email — nothing has changed.")
    text = f"{title}\n\n{lead}\n\n    {code}\n\n{footer}\n"
    return await mailer.send(email, subject, text, _wrap(title, lead, code, footer))
