"""
Encrypted local conversation memory.

Every exchange is appended to memory.enc (Fernet-encrypted JSON).
The key lives in .memory.key (gitignored, 0600, machine-local).

On each query Saira retrieves the N most semantically similar past
exchanges and injects them as context so she "remembers" past talks.
"""
from __future__ import annotations

import json
import logging
import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
from cryptography.fernet import Fernet

log = logging.getLogger(__name__)

KEY_FILE   = Path(".memory.key")
MEM_FILE   = Path("memory.enc")
MAX_STORED = 2000     # keep last N exchanges before trimming
TOP_K      = 4        # how many past exchanges to surface per query
SIM_FLOOR  = 0.30     # cosine similarity threshold

_lock = threading.Lock()

# In-memory cache
_exchanges: list[dict] = []          # [{ts, user, assistant}, ...]
_embeddings: Optional[np.ndarray] = None
_st_model = None
_embedded_count = 0                   # how many exchanges are already embedded


# ── Key management ───────────────────────────────────────────────────────────

def _get_or_create_key() -> bytes:
    if KEY_FILE.exists():
        return KEY_FILE.read_bytes()
    key = Fernet.generate_key()
    KEY_FILE.write_bytes(key)
    KEY_FILE.chmod(0o600)
    log.info("Generated new memory key at %s", KEY_FILE)
    return key


def _fernet() -> Fernet:
    return Fernet(_get_or_create_key())


# ── Persistence ──────────────────────────────────────────────────────────────

def _load_from_disk() -> list[dict]:
    if not MEM_FILE.exists():
        return []
    try:
        raw = _fernet().decrypt(MEM_FILE.read_bytes())
        return json.loads(raw)
    except Exception as exc:
        log.error("Failed to decrypt memory: %s — starting fresh", exc)
        return []


def _key(e: dict) -> tuple:
    return (e.get("ts", ""), e.get("user", ""), e.get("assistant", ""))


def _merge_with_disk(exchanges: list[dict]) -> list[dict]:
    """Union our in-RAM list with whatever is on disk now.

    A plain overwrite loses data whenever a second process is running — an
    import script, or another server instance — because each one holds the
    whole list in memory and writes its own stale snapshot over the file.
    """
    on_disk = _load_from_disk()
    if not on_disk:
        return exchanges
    merged = {_key(e): e for e in on_disk}
    merged.update({_key(e): e for e in exchanges})
    return sorted(merged.values(), key=lambda e: e.get("ts", ""))


def _save_to_disk(exchanges: list[dict]) -> None:
    try:
        raw = json.dumps(exchanges, ensure_ascii=False).encode()
        MEM_FILE.write_bytes(_fernet().encrypt(raw))
    except Exception as exc:
        log.error("Failed to save memory: %s", exc)


# ── Embedding model ──────────────────────────────────────────────────────────

def _get_model():
    global _st_model
    if _st_model is not None:
        return _st_model
    try:
        from sentence_transformers import SentenceTransformer
        _st_model = SentenceTransformer("all-MiniLM-L6-v2")
        log.info("Memory: sentence-transformer loaded")
    except Exception as exc:
        log.warning("sentence-transformers unavailable for memory: %s", exc)
    return _st_model


_TELUGU_RE = re.compile(r"[ఀ-౿]")


def _is_telugu(text: str) -> bool:
    return bool(_TELUGU_RE.search(text or ""))


def _script_matches(query: str, reply: str) -> bool:
    """True when a past reply is in the same script as the current question.

    Telling the model not to copy the wording is not enough — it still answers
    an English question in Telugu when a Telugu reply is sitting in context.
    So mismatched-script replies are withheld entirely. No facts are lost:
    name and location also live in the profile.
    """
    return _is_telugu(query) == _is_telugu(reply)


def _cosine_sim(query_vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    q = query_vec / (np.linalg.norm(query_vec) + 1e-9)
    m = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-9)
    return m @ q


# ── Public API ───────────────────────────────────────────────────────────────

def init() -> None:
    """Load memory from disk at startup."""
    global _exchanges, _embeddings, _embedded_count
    with _lock:
        _exchanges = _load_from_disk()
        _embeddings = None
        _embedded_count = 0
        log.info("Memory: loaded %d past exchanges", len(_exchanges))
    purge_bad_exchanges()  # drop refusals stored before the filter existed
    _get_model()  # warm the encoder so the first query isn't slow


# Replies that should never be remembered. Retrieval feeds past answers back as
# "You replied: …", so storing a refusal or an error teaches Saira to repeat it.
_BAD_REPLY_MARKERS = (
    "i dont have that capability",
    "i dont have that information",
    "i dont have access",
    "i dont have personal",
    "i cant do that",
    "i cant help",
    "im unable",
    "i am unable",
    "unable to provide",
    "as an ai",
    "i dont have the ability",
)


def _normalise(text: str) -> str:
    """Lowercase and flatten contractions so one marker matches every spelling
    of it — "don't", "dont" and "do not" all become "dont"."""
    t = text.lower().replace("'", "").replace("’", "")
    for long, short in (("do not", "dont"), ("cannot", "cant"),
                        ("can not", "cant"), ("i am", "im")):
        t = t.replace(long, short)
    return t


def is_worth_remembering(user: str, assistant: str) -> bool:
    """False for exchanges that would poison future retrieval."""
    u, a = (user or "").strip(), (assistant or "").strip()
    if not u or not a or len(a) < 3:
        return False
    norm = _normalise(a)
    return not any(marker in norm for marker in _BAD_REPLY_MARKERS)


def purge_bad_exchanges() -> int:
    """Drop already-stored refusals/errors. Returns how many were removed."""
    global _exchanges, _embeddings, _embedded_count
    with _lock:
        before = len(_exchanges)
        _exchanges = [
            e for e in _exchanges
            if is_worth_remembering(e.get("user", ""), e.get("assistant", ""))
        ]
        removed = before - len(_exchanges)
        if removed:
            _embeddings = None      # matrix no longer lines up with the list
            _embedded_count = 0
            _save_to_disk(_exchanges)
            log.info("Memory: purged %d unusable exchanges", removed)
    return removed


def save_exchange(user: str, assistant: str) -> None:
    """Append a new exchange and persist encrypted to disk."""
    global _exchanges, _embeddings, _embedded_count
    if not is_worth_remembering(user, assistant):
        log.info("Memory: skipping unusable exchange (%r)", (assistant or "")[:60])
        return
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "user": user,
        "assistant": assistant,
    }
    with _lock:
        _exchanges.append(entry)
        merged = _merge_with_disk(_exchanges)
        if len(merged) > MAX_STORED:
            merged = merged[-MAX_STORED:]
        # Anything another process added shifts our indices, so the cached
        # embedding matrix no longer lines up with the list.
        if len(merged) != len(_exchanges):
            _embeddings = None
            _embedded_count = 0
        _exchanges = merged
        _save_to_disk(_exchanges)


def get_relevant_context(query: str, top_k: int = TOP_K) -> str:
    """Return a formatted block of the most relevant past exchanges."""
    global _embeddings, _embedded_count

    with _lock:
        exchanges = list(_exchanges)

    if not exchanges:
        return ""

    model = _get_model()
    if model is None:
        # fallback: return last 3 exchanges as plain text
        recent = exchanges[-3:]
        lines = ["Relevant past conversations:"]
        for e in recent:
            lines.append(f'User said: "{e["user"]}"')
            lines.append(f'You replied: "{e["assistant"]}"')
        return "\n".join(lines)

    # Encode only exchanges added since the last call, then append to the matrix
    with _lock:
        if _embedded_count < len(exchanges):
            new_texts = [e["user"] for e in exchanges[_embedded_count:]]
            new_vecs = model.encode(new_texts, convert_to_numpy=True).astype(np.float32)
            _embeddings = new_vecs if _embeddings is None else np.vstack([_embeddings, new_vecs])
            _embedded_count = len(exchanges)

    if _embeddings is None or _embeddings.shape[0] == 0:
        return ""

    try:
        qvec = model.encode([query], convert_to_numpy=True)[0].astype(np.float32)
        sims = _cosine_sim(qvec, _embeddings)
        top_idx = np.argsort(sims)[::-1][:top_k]

        chosen = [
            (exchanges[i], float(sims[i]))
            for i in top_idx
            if float(sims[i]) >= SIM_FLOOR
            and _script_matches(query, exchanges[i].get("assistant", ""))
        ]

        if not chosen:
            return ""

        # Framed as background, not as a template. Without this the model
        # copies an old reply wholesale — answering an English question in
        # Telugu, or using a form of address the user has since changed.
        lines = [
            "Background from past conversations with the user. Use these only "
            "to recall FACTS. Do NOT copy the wording, the language, or the "
            "form of address — those replies may be outdated. Answer in the "
            "language of the user's current message and follow the standing "
            "instructions above.",
        ]
        for ex, _ in chosen:
            lines.append(f'[{ex["ts"]}] User: "{ex["user"][:120]}"')
            lines.append(f'You replied: "{ex["assistant"][:200]}"')
            lines.append("")

        return "\n".join(lines)
    except Exception as exc:
        log.warning("Memory retrieval error: %s", exc)
        return ""
