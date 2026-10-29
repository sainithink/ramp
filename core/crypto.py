"""Per-user encryption for stored personal data.

Replaces the old scheme of one key file per data type (.memory.key,
.prefs.key, .profile.key) shared by everyone. With multiple tenants a single
key would let any leaked blob be opened with the same secret, so instead a
server master key derives a distinct key per (user, kind) via HKDF.

Consequences worth knowing:
  * The master key is the only secret to protect or rotate.
  * Losing it makes every stored blob permanently unreadable — that is the
    intended property, not a bug. Back it up outside the database.
  * The database alone reveals nothing; rows are Fernet tokens.
"""
from __future__ import annotations

import base64
import logging
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

log = logging.getLogger(__name__)

MASTER_KEY_FILE = Path(".master.key")
_master: bytes | None = None


def _load_master() -> bytes:
    """Master key from env, else a gitignored local file, generated on first use."""
    global _master
    if _master is not None:
        return _master

    env = os.environ.get("SAIRA_MASTER_KEY")
    if env:
        _master = env.encode()
        return _master

    if MASTER_KEY_FILE.exists():
        _master = MASTER_KEY_FILE.read_bytes()
        return _master

    _master = base64.urlsafe_b64encode(os.urandom(32))
    MASTER_KEY_FILE.write_bytes(_master)
    MASTER_KEY_FILE.chmod(0o600)
    log.warning(
        "Generated a new master key at %s. Back this up — without it every "
        "stored conversation, preference and profile becomes unreadable.",
        MASTER_KEY_FILE,
    )
    return _master


def _fernet_for(user_id: str, kind: str) -> Fernet:
    """Derive a Fernet key unique to this user and this kind of data."""
    derived = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=user_id.encode(),
        info=f"saira:{kind}".encode(),
    ).derive(_load_master())
    return Fernet(base64.urlsafe_b64encode(derived))


def encrypt(user_id: str, kind: str, plaintext: str) -> str:
    return _fernet_for(user_id, kind).encrypt(plaintext.encode()).decode()


def decrypt(user_id: str, kind: str, token: str) -> str | None:
    """Return plaintext, or None when the token is absent or undecryptable.

    Callers treat None as "no data yet" so a rotated or missing master key
    degrades to an empty profile rather than crashing the session.
    """
    if not token:
        return None
    try:
        return _fernet_for(user_id, kind).decrypt(token.encode()).decode()
    except (InvalidToken, ValueError) as exc:
        log.error("Could not decrypt %s for user %s: %s", kind, user_id[:8], exc)
        return None
