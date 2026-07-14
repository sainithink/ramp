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
_dirty = False                        # embeddings need rebuild


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


def _build_embeddings(exchanges: list[dict]) -> Optional[np.ndarray]:
    model = _get_model()
    if model is None or not exchanges:
        return None
    texts = [e["user"] for e in exchanges]
    return model.encode(texts, convert_to_numpy=True).astype(np.float32)


def _cosine_sim(query_vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    q = query_vec / (np.linalg.norm(query_vec) + 1e-9)
    m = matrix / (np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-9)
    return m @ q


# ── Public API ───────────────────────────────────────────────────────────────

def init() -> None:
    """Load memory from disk at startup."""
    global _exchanges, _embeddings, _dirty
    with _lock:
        _exchanges = _load_from_disk()
        _dirty = True
        log.info("Memory: loaded %d past exchanges", len(_exchanges))


def save_exchange(user: str, assistant: str) -> None:
    """Append a new exchange and persist encrypted to disk."""
    global _exchanges, _dirty
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "user": user,
        "assistant": assistant,
    }
    with _lock:
        _exchanges.append(entry)
        # trim oldest if over limit
        if len(_exchanges) > MAX_STORED:
            _exchanges = _exchanges[-MAX_STORED:]
        _save_to_disk(_exchanges)
        _dirty = True


def get_relevant_context(query: str, top_k: int = TOP_K) -> str:
    """Return a formatted block of the most relevant past exchanges."""
    global _embeddings, _dirty

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

    # Rebuild embeddings if new exchanges added
    with _lock:
        if _dirty or _embeddings is None or len(_embeddings) != len(exchanges):
            _embeddings = _build_embeddings(exchanges)
            _dirty = False

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
        ]

        if not chosen:
            return ""

        lines = ["Here are relevant things from your past conversations with the user:"]
        for ex, _ in chosen:
            lines.append(f'[{ex["ts"]}] User: "{ex["user"][:120]}"')
            lines.append(f'You replied: "{ex["assistant"][:200]}"')
            lines.append("")

        return "\n".join(lines)
    except Exception as exc:
        log.warning("Memory retrieval error: %s", exc)
        return ""
