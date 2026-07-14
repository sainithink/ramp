"""
DPO few-shot retrieval: given a user query, find the N most similar (prompt, response)
pairs from the downloaded dataset and return them as few-shot examples for the LLM.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

import numpy as np

log = logging.getLogger(__name__)

DATA_PATH = Path(__file__).parent.parent / "data" / "dpo_examples.json"
TOP_K     = 3     # examples to inject per query
SIM_THRESHOLD = 0.35  # cosine similarity floor — skip weak matches

_examples: Optional[list[dict]] = None
_embeddings: Optional[np.ndarray] = None
_st_model = None


def _load():
    global _examples, _embeddings, _st_model
    if _examples is not None:
        return

    if not DATA_PATH.exists():
        log.info("DPO dataset not found at %s — run scripts/fetch_dpo_dataset.py", DATA_PATH)
        _examples = []
        _embeddings = np.empty((0, 0))
        return

    log.info("Loading DPO examples from %s …", DATA_PATH)
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    _examples  = payload["examples"]
    _embeddings = np.array(payload["embeddings"], dtype=np.float32)

    embed_model = payload.get("embed_model", "all-MiniLM-L6-v2")
    try:
        from sentence_transformers import SentenceTransformer
        _st_model = SentenceTransformer(embed_model)
        log.info("DPO: loaded %d examples, embed model '%s'", len(_examples), embed_model)
    except Exception as exc:
        log.warning("sentence-transformers unavailable: %s — DPO disabled", exc)
        _examples = []


def _cosine(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = a / (np.linalg.norm(a) + 1e-9)
    b = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-9)
    return b @ a


def get_few_shot_examples(query: str, top_k: int = TOP_K) -> str:
    """Return a formatted few-shot block for injection into the system prompt."""
    _load()
    if not _examples or _st_model is None:
        return ""

    try:
        qvec = _st_model.encode([query], convert_to_numpy=True)[0].astype(np.float32)
        sims = _cosine(qvec, _embeddings)
        top_idx = np.argsort(sims)[::-1][:top_k]

        chosen = [
            (_examples[i], float(sims[i]))
            for i in top_idx
            if float(sims[i]) >= SIM_THRESHOLD
        ]

        if not chosen:
            return ""

        lines = ["Here are examples of good, natural human-like responses for similar questions:"]
        for ex, score in chosen:
            lines.append(f'Q: {ex["prompt"][:120]}')
            lines.append(f'A: {ex["response"][:200]}')
            lines.append("")

        return "\n".join(lines)
    except Exception as exc:
        log.warning("DPO retrieval error: %s", exc)
        return ""
