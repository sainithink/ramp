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
    _get_model()  # warm the encoder so the first query isn't slow


def save_exchange(user: str, assistant: str) -> None:
    """Append a new exchange and persist encrypted to disk."""
    global _exchanges, _embeddings, _embedded_count
    entry = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "user": user,
        "assistant": assistant,
    }
    with _lock:
        _exchanges.append(entry)
        # trim oldest if over limit — invalidates the embedding cache
        if len(_exchanges) > MAX_STORED:
            _exchanges = _exchanges[-MAX_STORED:]
            _embeddings = None
            _embedded_count = 0
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
