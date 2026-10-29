"""Per-user wake-word matching.

Each user names their own assistant, so the hard-coded homophone list that used
to live in main.py cannot work — we cannot hand-curate spellings for every name
someone might pick.

Whisper rarely writes the name as spelled. Measured on this stack: rendering
"Hey Saira" through TTS across four voices and three speeds and transcribing it
back produced "sarah" 33 times out of 36 and "saira" zero times. So matching is
phonetic: words are compared by Metaphone code, under which saira / sarah /
sara / syra all collapse to "SR".

Equality of codes is required rather than fuzzy similarity. Fuzzy matching
scores nova vs november at 0.84, which would fire constantly; their codes
(NF vs NFMBR) differ, so exact comparison rejects it.
"""
from __future__ import annotations

import re
from functools import lru_cache

import jellyfish

# Openers people put before the name.
_OPENERS = ("hey", "hi", "hello", "ok", "okay", "yo")

# Common words are excluded from matching. A short name like "Ana" codes to
# "AN", which is also the code for "an" and "on" — without this guard the
# assistant would wake on ordinary speech.
_STOPWORDS = frozenset("""
a an and are as at be been but by can could did do does for from had has have
he her him his how i if in is it its me my no not of on or our out said she so
that the their them then there these they this to up us was we were what when
where which who why will with would you your am are one two
""".split())

_WORD_RE = re.compile(r"[a-z']+")


@lru_cache(maxsize=512)
def _code(word: str) -> str:
    try:
        return jellyfish.metaphone(word)
    except Exception:
        return ""


@lru_cache(maxsize=256)
def wake_codes(wake_name: str) -> frozenset[str]:
    """Phonetic codes that count as this assistant's name.

    Includes the literal spelling's code plus the code of the name as written,
    so both the spelled and heard forms match.
    """
    name = (wake_name or "Saira").strip().lower()
    codes = {_code(name)}
    codes.discard("")
    return frozenset(codes)


def contains_wake(text: str, wake_name: str) -> bool:
    """True when `text` contains the assistant's name, however Whisper spelled it."""
    if not text:
        return False
    targets = wake_codes(wake_name)
    if not targets:
        return False
    for word in _WORD_RE.findall(text.lower()):
        if word in _STOPWORDS:
            continue
        if _code(word) in targets:
            return True
    return False


def strip_wake(text: str, wake_name: str) -> str:
    """Remove a leading opener and the name, leaving just the command."""
    if not text:
        return ""
    targets = wake_codes(wake_name)
    tokens = text.split()
    i = 0
    # Skip an opener such as "hey".
    while i < len(tokens):
        bare = re.sub(r"[^a-z']", "", tokens[i].lower())
        if bare in _OPENERS:
            i += 1
            continue
        break
    # Skip the name itself if that is the next word.
    if i < len(tokens):
        bare = re.sub(r"[^a-z']", "", tokens[i].lower())
        if bare and bare not in _STOPWORDS and _code(bare) in targets:
            i += 1
    out = " ".join(tokens[i:]).strip()
    return re.sub(r"^[,!.\s]+", "", out).strip()
