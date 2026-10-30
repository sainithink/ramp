"""Outgoing email over plain SMTP.

Deliberately not tied to one provider: anything that speaks SMTP works —
Gmail with an app password, Brevo, Mailgun, Postmark, SES. Configure it with

    SAIRA_SMTP_HOST=smtp.gmail.com
    SAIRA_SMTP_PORT=587          # 587 STARTTLS (default), 465 implicit TLS
    SAIRA_SMTP_USER=you@gmail.com
    SAIRA_SMTP_PASSWORD=...      # an app password, never the account password
    SAIRA_MAIL_FROM="Saira <you@gmail.com>"
    SAIRA_APP_URL=https://saira.sainith.in

With nothing configured, mail is written to the log instead of sent, so the
whole flow can be exercised locally without credentials. That fallback is for
development only — `configured()` is false and the caller says so.
"""
from __future__ import annotations

import asyncio
import logging
import os
import smtplib
import ssl
from email.message import EmailMessage

log = logging.getLogger(__name__)

TIMEOUT = 20


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or default).strip()


def configured() -> bool:
    return bool(_env("SAIRA_SMTP_HOST"))


def app_url() -> str:
    return _env("SAIRA_APP_URL", "http://localhost:3001").rstrip("/")


def _sender() -> str:
    return _env("SAIRA_MAIL_FROM") or _env("SAIRA_SMTP_USER") or "saira@localhost"


def _send_blocking(msg: EmailMessage) -> None:
    host = _env("SAIRA_SMTP_HOST")
    port = int(_env("SAIRA_SMTP_PORT", "587"))
    user = _env("SAIRA_SMTP_USER")
    password = _env("SAIRA_SMTP_PASSWORD")
    context = ssl.create_default_context()

    # 465 is TLS from the first byte; 587 opens plain and upgrades.
    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=TIMEOUT, context=context) as smtp:
            if user:
                smtp.login(user, password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=TIMEOUT) as smtp:
            smtp.ehlo()
            smtp.starttls(context=context)
            smtp.ehlo()
            if user:
                smtp.login(user, password)
            smtp.send_message(msg)


async def send(to: str, subject: str, text: str, html: str | None = None) -> bool:
    """Send one message. Returns False when it could not be delivered."""
    msg = EmailMessage()
    msg["From"] = _sender()
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(text)
    if html:
        msg.add_alternative(html, subtype="html")

    if not configured():
        log.warning("SMTP is not configured — email to %s was not sent.\n"
                    "--- %s ---\n%s\n--- end ---", to, subject, text)
        return False

    try:
        # smtplib is blocking, and blocking the event loop would stall every
        # other websocket on the server while a mail server thinks about it.
        await asyncio.to_thread(_send_blocking, msg)
        log.info("Sent %r to %s", subject, to)
        return True
    except Exception as exc:
        log.error("Could not send mail to %s: %s", to, exc)
        return False
