"""Per-user memory, preferences and profile.

Previously each of these was module-level state backed by one file on disk —
fine for a single user, a privacy breach the moment a second one exists, since
every session would read and write the same `_exchanges` list.

Here each user gets their own store, encrypted under a key derived from their
id (core/crypto.py) and persisted as a row in user_blobs. The extraction and
filtering logic is imported from the original modules rather than copied, so
the behaviour that was tested there still applies:

  * memory.is_worth_remembering  — refusals are never stored, because retrieval
    replays past answers and would teach the model to repeat them
  * memory._script_matches       — a Telugu reply is withheld from an English
    question, otherwise the model answers in the wrong language
  * preferences.extract          — "call me Sai" becomes a standing rule

The sentence-transformer stays a single shared instance: it is read-only and
loading one per user would cost ~0.2 GB each.
"""
from __future__ import annotations

import json
import logging
import threading
from datetime import datetime
from typing import Optional

import numpy as np

from core import crypto, memory as mem_logic, preferences as pref_logic
from core.db import UserBlob, get_session

log = logging.getLogger(__name__)

MAX_STORED = mem_logic.MAX_STORED
TOP_K = mem_logic.TOP_K
SIM_FLOOR = mem_logic.SIM_FLOOR


# ── Blob persistence ─────────────────────────────────────────────────────────

def _read_blob(user_id: str, kind: str) -> Optional[str]:
    with get_session() as s:
        row = s.get(UserBlob, (user_id, kind))
        if not row or not row.payload:
            return None
    return crypto.decrypt(user_id, kind, row.payload)


def _write_blob(user_id: str, kind: str, plaintext: str) -> None:
    token = crypto.encrypt(user_id, kind, plaintext)
    with get_session() as s:
        row = s.get(UserBlob, (user_id, kind))
        if row is None:
            s.add(UserBlob(user_id=user_id, kind=kind, payload=token))
        else:
            row.payload = token
            row.updated_at = datetime.utcnow()
        s.commit()


# ── Memory ───────────────────────────────────────────────────────────────────

class MemoryStore:
    """One user's conversation history plus its embedding cache."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self._lock = threading.Lock()
        self._exchanges: list[dict] = []
        self._embeddings: Optional[np.ndarray] = None
        self._embedded = 0
        self._load()

    def _load(self) -> None:
        raw = _read_blob(self.user_id, "memory")
        if raw:
            try:
                self._exchanges = json.loads(raw)
            except json.JSONDecodeError:
                log.error("Corrupt memory blob for %s — starting fresh", self.user_id[:8])
                self._exchanges = []
        # Drop refusals stored before the filter existed.
        keep = [e for e in self._exchanges
                if mem_logic.is_worth_remembering(e.get("user", ""), e.get("assistant", ""))]
        if len(keep) != len(self._exchanges):
            log.info("Memory: purged %d unusable exchanges for %s",
                     len(self._exchanges) - len(keep), self.user_id[:8])
            self._exchanges = keep
            self._persist()

    def _persist(self) -> None:
        _write_blob(self.user_id, "memory",
                    json.dumps(self._exchanges, ensure_ascii=False))

    def save_exchange(self, user_text: str, assistant_text: str) -> None:
        if not mem_logic.is_worth_remembering(user_text, assistant_text):
            log.info("Memory: skipping unusable exchange for %s", self.user_id[:8])
            return
        with self._lock:
            self._exchanges.append({
                "ts": datetime.now().isoformat(timespec="seconds"),
                "user": user_text,
                "assistant": assistant_text,
            })
            if len(self._exchanges) > MAX_STORED:
                self._exchanges = self._exchanges[-MAX_STORED:]
                self._embeddings, self._embedded = None, 0
            self._persist()

    def get_relevant_context(self, query: str, top_k: int = TOP_K) -> str:
        with self._lock:
            exchanges = list(self._exchanges)
        if not exchanges:
            return ""

        model = mem_logic._get_model()
        if model is None:
            recent = exchanges[-3:]
            lines = ["Relevant past conversations:"]
            for e in recent:
                lines.append(f'User said: "{e["user"]}"')
                lines.append(f'You replied: "{e["assistant"]}"')
            return "\n".join(lines)

        # Encode only what is new, then append to the matrix.
        with self._lock:
            if self._embedded < len(exchanges):
                texts = [e["user"] for e in exchanges[self._embedded:]]
                vecs = model.encode(texts, convert_to_numpy=True).astype(np.float32)
                self._embeddings = vecs if self._embeddings is None \
                    else np.vstack([self._embeddings, vecs])
                self._embedded = len(exchanges)

        if self._embeddings is None or self._embeddings.shape[0] == 0:
            return ""
        try:
            qvec = model.encode([query], convert_to_numpy=True)[0].astype(np.float32)
            sims = mem_logic._cosine_sim(qvec, self._embeddings)
            top = np.argsort(sims)[::-1][:top_k]
            chosen = [exchanges[i] for i in top
                      if float(sims[i]) >= SIM_FLOOR
                      and mem_logic._script_matches(query, exchanges[i].get("assistant", ""))]
            if not chosen:
                return ""
            lines = [
                "Background from past conversations with the user. Use these only "
                "to recall FACTS. Do NOT copy the wording, the language, or the "
                "form of address — those replies may be outdated. Answer in the "
                "language of the user's current message and follow the standing "
                "instructions above.",
            ]
            for e in chosen:
                lines.append(f'[{e["ts"]}] User: "{e["user"][:120]}"')
                lines.append(f'You replied: "{e["assistant"][:200]}"')
                lines.append("")
            return "\n".join(lines)
        except Exception as exc:
            log.warning("Memory retrieval error for %s: %s", self.user_id[:8], exc)
            return ""

    def count(self) -> int:
        return len(self._exchanges)


# ── Preferences ──────────────────────────────────────────────────────────────

class PreferenceStore:
    """One user's standing instructions ("call me Sai")."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self._lock = threading.Lock()
        self._prefs: dict[str, dict] = {}
        raw = _read_blob(user_id, "preferences")
        if raw:
            try:
                self._prefs = json.loads(raw)
            except json.JSONDecodeError:
                log.error("Corrupt preferences blob for %s", user_id[:8])

    def _persist(self) -> None:
        _write_blob(self.user_id, "preferences",
                    json.dumps(self._prefs, ensure_ascii=False))

    def learn(self, text: str) -> list[str]:
        added: list[str] = []
        with self._lock:
            for kind, rule in pref_logic.extract(text):
                if self._prefs.get(kind, {}).get("text") == rule:
                    continue
                self._prefs[kind] = {
                    "text": rule,
                    "ts": datetime.now().isoformat(timespec="seconds"),
                }
                added.append(rule)
            if added:
                self._persist()
        for r in added:
            log.info("Learned preference for %s: %s", self.user_id[:8], r)
        return added

    def as_prompt(self) -> str:
        with self._lock:
            rules = [p["text"] for p in self._prefs.values()]
        if not rules:
            return ""
        lines = ["STANDING INSTRUCTIONS FROM THE USER — these override everything "
                 "else and apply to every reply:"]
        lines += [f"  • {r}" for r in rules]
        return "\n".join(lines)

    def all(self) -> dict[str, dict]:
        with self._lock:
            return dict(self._prefs)

    def forget(self, kind: str) -> bool:
        with self._lock:
            if kind in self._prefs:
                del self._prefs[kind]
                self._persist()
                return True
        return False


# ── Profile ──────────────────────────────────────────────────────────────────

class ProfileStore:
    """Facts the user gave about themselves (name, location, job, interests)."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self._data: dict[str, str] = {}
        raw = _read_blob(user_id, "profile")
        if raw:
            try:
                self._data = json.loads(raw)
            except json.JSONDecodeError:
                log.error("Corrupt profile blob for %s", user_id[:8])

    def set(self, data: dict) -> None:
        self._data = {k: v for k, v in data.items() if v}
        _write_blob(self.user_id, "profile",
                    json.dumps(self._data, ensure_ascii=False))

    def all(self) -> dict[str, str]:
        return dict(self._data)

    def as_prompt(self) -> str:
        if not self._data:
            return ""
        lines = ["## Personal context about the user:"]
        lines += [f"- {k}: {v}" for k, v in self._data.items() if v]
        return "\n".join(lines)


# ── Per-user bundle, cached while the user is connected ──────────────────────

class UserContext:
    def __init__(self, user_id: str, wake_name: str = "Saira"):
        self.user_id = user_id
        self.wake_name = wake_name
        self.memory = MemoryStore(user_id)
        self.preferences = PreferenceStore(user_id)
        self.profile = ProfileStore(user_id)


_contexts: dict[str, UserContext] = {}
_contexts_lock = threading.Lock()


def get_context(user_id: str, wake_name: str = "Saira") -> UserContext:
    """Return this user's stores, building them on first use.

    Cached so reconnecting does not re-read and re-embed everything, and so two
    concurrent sessions for the same user share one consistent view.
    """
    with _contexts_lock:
        ctx = _contexts.get(user_id)
        if ctx is None:
            ctx = UserContext(user_id, wake_name)
            _contexts[user_id] = ctx
        else:
            ctx.wake_name = wake_name
        return ctx


def drop_context(user_id: str) -> None:
    with _contexts_lock:
        _contexts.pop(user_id, None)
