"""
Encrypted personal profile — loaded at runtime, never stored in plain text.
Key is machine-local (.profile.key, gitignored). Profile stored in profile.enc.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from cryptography.fernet import Fernet

log = logging.getLogger(__name__)

KEY_FILE    = Path(".profile.key")
PROFILE_ENC = Path("profile.enc")

_profile_text: str = ""


def _get_or_create_key() -> bytes:
    if KEY_FILE.exists():
        return KEY_FILE.read_bytes()
    key = Fernet.generate_key()
    KEY_FILE.write_bytes(key)
    KEY_FILE.chmod(0o600)  # owner read/write only
    log.info("Generated new profile key at %s", KEY_FILE)
    return key


def save_profile(data: dict) -> None:
    key   = _get_or_create_key()
    fernet = Fernet(key)
    plaintext = json.dumps(data, indent=2).encode()
    PROFILE_ENC.write_bytes(fernet.encrypt(plaintext))
    log.info("Profile saved (encrypted) to %s", PROFILE_ENC)


def load_profile() -> str:
    global _profile_text
    if not PROFILE_ENC.exists():
        log.warning("No profile.enc found — Jarvis has no personal context.")
        return ""
    try:
        key    = _get_or_create_key()
        fernet = Fernet(key)
        data   = json.loads(fernet.decrypt(PROFILE_ENC.read_bytes()))
        lines  = ["## Personal context about the user:"]
        for k, v in data.items():
            if v:
                lines.append(f"- {k}: {v}")
        _profile_text = "\n".join(lines)
        log.info("Profile loaded (%d fields)", len(data))
        return _profile_text
    except Exception as exc:
        log.error("Failed to load profile: %s", exc)
        return ""


def get_profile_text() -> str:
    return _profile_text
