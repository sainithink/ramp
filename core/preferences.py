"""Standing preferences the user states out loud.

Conversation memory is retrieved *semantically*, so "call me Sai" only comes
back when the current question happens to resemble it. A standing instruction
has to apply to every reply, so those are pulled out and stored separately,
then injected into every system prompt.

Stored Fernet-encrypted in preferences.enc, key in .prefs.key (0600,
gitignored) — same machine-local approach as profile and memory.
"""
from __future__ import annotations

import json
import logging
import re
import threading
from datetime import datetime
from pathlib import Path

from cryptography.fernet import Fernet

log = logging.getLogger(__name__)

KEY_FILE  = Path(".prefs.key")
PREF_FILE = Path("preferences.enc")

_lock = threading.Lock()
_prefs: dict[str, dict] = {}   # kind -> {"text": …, "ts": …}


# ── Key / persistence ────────────────────────────────────────────────────────

def _get_or_create_key() -> bytes:
    if KEY_FILE.exists():
        return KEY_FILE.read_bytes()
    key = Fernet.generate_key()
    KEY_FILE.write_bytes(key)
    KEY_FILE.chmod(0o600)
    log.info("Generated new preferences key at %s", KEY_FILE)
    return key


def _fernet() -> Fernet:
    return Fernet(_get_or_create_key())


def _load() -> dict[str, dict]:
    if not PREF_FILE.exists():
        return {}
    try:
        return json.loads(_fernet().decrypt(PREF_FILE.read_bytes()))
    except Exception as exc:
        log.error("Failed to decrypt preferences: %s — starting fresh", exc)
        return {}


def _save(prefs: dict[str, dict]) -> None:
    try:
        raw = json.dumps(prefs, ensure_ascii=False).encode()
        PREF_FILE.write_bytes(_fernet().encrypt(raw))
    except Exception as exc:
        log.error("Failed to save preferences: %s", exc)


# ── Extraction ───────────────────────────────────────────────────────────────

# "call me later/back/tomorrow" is not a name.
_NOT_A_NAME = {
    "later", "back", "tomorrow", "now", "when", "if", "again", "soon",
    "after", "before", "tonight", "today", "anytime", "whenever", "please",
}

# Each entry: kind, pattern, formatter. `kind` makes a newer statement of the
# same sort replace the older one instead of piling up contradictions.
_RULES: list[tuple[str, re.Pattern, object]] = [
    ("address_as",
     re.compile(r"\bcall me(?:\s+as)?\s+([A-Za-z][\w'’-]{1,20})", re.I),
     lambda m: f'Always address the user as "{m.group(1).strip().title()}" — '
               f'use this name, not their full name.'),

    ("address_as",
     re.compile(r"\b(?:my name is|i am|i'm)\s+([A-Za-z][\w'’-]{1,20})\s*,?\s*"
                r"(?:not|and not)\b", re.I),
     lambda m: f'Always address the user as "{m.group(1).strip().title()}".'),

    ("never",
     re.compile(r"\b(?:never|don'?t ever|do not ever)\s+(.{4,110})", re.I),
     lambda m: f"Never {_clean(m.group(1))}."),

    ("always",
     re.compile(r"\b(?:from now on|always)\s*,?\s+(.{4,110})", re.I),
     lambda m: f"Always {_clean(m.group(1))}."),

    ("remember",
     re.compile(r"\bremember\s+(?:that\s+)?(.{4,110})", re.I),
     lambda m: f"Remember: {_clean(m.group(1))}."),

    ("prefers",
     re.compile(r"\bi (?:prefer|like it when|want you to)\s+(.{4,110})", re.I),
     lambda m: f"The user prefers: {_clean(m.group(1))}."),
]


def _clean(text: str) -> str:
    return re.sub(r"\s{2,}", " ", text).strip().rstrip(".!?,")


def extract(text: str) -> list[tuple[str, str]]:
    """Return [(kind, rule_text)] for any standing instructions in `text`."""
    if not text:
        return []
    found: list[tuple[str, str]] = []
    seen_kinds: set[str] = set()
    for kind, pattern, fmt in _RULES:
        m = pattern.search(text)
        if not m:
            continue
        if kind == "address_as" and m.group(1).lower() in _NOT_A_NAME:
            continue
        if kind in seen_kinds:      # first rule of a kind wins within one utterance
            continue
        rule = fmt(m)
        # "call me sai, always call me sai only" would otherwise yield a second
        # rule restating the name in the user's own voice ("Always call me …"),
        # which reads as nonsense addressed to Saira.
        if kind in ("always", "never") and "address_as" in seen_kinds \
                and re.search(r"\bcall (me|him|her|them)\b", rule, re.I):
            continue
        seen_kinds.add(kind)
        found.append((kind, rule))
    return found


# ── Public API ───────────────────────────────────────────────────────────────

def init() -> None:
    global _prefs
    with _lock:
        _prefs = _load()
        log.info("Preferences: loaded %d standing rules", len(_prefs))


def learn(text: str) -> list[str]:
    """Pull any standing instructions out of `text` and persist them."""
    global _prefs
    new = extract(text)
    if not new:
        return []
    added: list[str] = []
    with _lock:
        for kind, rule in new:
            if _prefs.get(kind, {}).get("text") == rule:
                continue   # already known
            _prefs[kind] = {"text": rule,
                            "ts": datetime.now().isoformat(timespec="seconds")}
            added.append(rule)
        if added:
            _save(_prefs)
    for rule in added:
        log.info("Learned preference: %s", rule)
    return added


def get_preferences_text() -> str:
    with _lock:
        rules = [p["text"] for p in _prefs.values()]
    if not rules:
        return ""
    lines = ["STANDING INSTRUCTIONS FROM THE USER — these override everything "
             "else and apply to every reply:"]
    lines += [f"  • {r}" for r in rules]
    return "\n".join(lines)


def all_preferences() -> dict[str, dict]:
    with _lock:
        return dict(_prefs)


def forget(kind: str) -> bool:
    global _prefs
    with _lock:
        if kind in _prefs:
            del _prefs[kind]
            _save(_prefs)
            return True
    return False
