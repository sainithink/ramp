"""
Download Human-Like-DPO dataset from HuggingFace and extract chosen responses.

Saves embeddings + examples to data/dpo_examples.json for use in Jarvis.

Run once (or re-run to refresh):
    .venv/bin/python3.14 scripts/fetch_dpo_dataset.py
"""

import json
import os
import sys

# ── ensure we run inside the project venv ─────────────────────────────────────
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV_PYTHON  = os.path.join(PROJECT_ROOT, ".venv", "bin", "python3.14")

if sys.executable != VENV_PYTHON and os.path.exists(VENV_PYTHON):
    import subprocess
    subprocess.exec(VENV_PYTHON, [VENV_PYTHON] + sys.argv)

import re
from pathlib import Path

import numpy as np
from datasets import load_dataset
from sentence_transformers import SentenceTransformer

# ── Configuration ─────────────────────────────────────────────────────────────
# Several good human-like DPO datasets on HuggingFace:
#   "jondurbin/truthy-dpo-v0.1"        — factual Q&A, 1 k rows
#   "HuggingFaceH4/ultrafeedback_binarized" — general chat, 200 k rows
#   "Intel/orca_dpo_pairs"             — step-by-step reasoning
#   "argilla/dpo-mix-7k"               — diverse conversation mix
DATASETS = [
    {
        "name": "jondurbin/truthy-dpo-v0.1",
        "split": "train",
        "format": "standard",   # has separate 'prompt' and 'chosen' string fields
        "max_rows": 500,
    },
    {
        "name": "argilla/dpo-mix-7k",
        "split": "train",
        "format": "chat",       # 'chosen' is a list of {role, content} dicts
        "max_rows": 1000,
    },
]

OUTPUT_PATH = Path(PROJECT_ROOT) / "data" / "dpo_examples.json"
EMBED_MODEL = "all-MiniLM-L6-v2"   # fast, ~80 MB
MAX_CHOSEN_WORDS = 80               # skip very long responses (not voice-friendly)
MIN_CHOSEN_WORDS = 3


def _extract_standard(row) -> tuple[str, str]:
    """Extract (prompt, chosen_response) from standard format with separate fields."""
    prompt  = _clean(row.get("prompt", "") or "")
    chosen  = _clean(_extract_chat_response(row.get("chosen", "")) or "")
    return prompt, chosen


def _extract_chat(row) -> tuple[str, str]:
    """Extract (prompt, chosen_response) from chat-format (list of {role,content})."""
    messages = row.get("chosen", [])
    if not isinstance(messages, list):
        return "", ""
    prompt   = ""
    response = ""
    for msg in messages:
        role    = msg.get("role", "")
        content = _clean(msg.get("content", ""))
        if role == "user" and not prompt:
            prompt = content
        elif role == "assistant":
            response = content
    return prompt, response


def _extract_chat_response(value) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        for msg in value:
            if msg.get("role") == "assistant":
                return msg.get("content", "")
    return ""


def _clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_examples() -> list[dict]:
    examples = []
    for cfg in DATASETS:
        print(f"\n▶ Loading {cfg['name']} …")
        try:
            ds = load_dataset(cfg["name"], split=cfg["split"], streaming=False)
        except Exception as e:
            print(f"  ✗ Failed: {e}")
            continue

        fmt = cfg.get("format", "standard")
        count = 0
        for row in ds:
            if count >= cfg["max_rows"]:
                break

            if fmt == "chat":
                prompt, chosen = _extract_chat(row)
            else:
                prompt, chosen = _extract_standard(row)

            if not prompt or not chosen:
                continue
            words = len(chosen.split())
            if words < MIN_CHOSEN_WORDS or words > MAX_CHOSEN_WORDS:
                continue
            # Skip if chosen looks like a list/markdown (not voice-friendly)
            if chosen.startswith("#") or "\n-" in chosen or "\n*" in chosen:
                continue

            examples.append({"prompt": prompt, "response": chosen})
            count += 1

        print(f"  ✓ Collected {count} examples")

    print(f"\nTotal examples: {len(examples)}")
    return examples


def build_embeddings(examples: list[dict]) -> np.ndarray:
    print(f"\n▶ Building embeddings with '{EMBED_MODEL}' …")
    model = SentenceTransformer(EMBED_MODEL)
    prompts = [e["prompt"] for e in examples]
    embeddings = model.encode(prompts, show_progress_bar=True, convert_to_numpy=True)
    print(f"  ✓ Embeddings shape: {embeddings.shape}")
    return embeddings


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    examples = fetch_examples()
    if not examples:
        print("No examples collected — check dataset names / network.")
        sys.exit(1)

    embeddings = build_embeddings(examples)

    payload = {
        "examples": examples,
        "embeddings": embeddings.tolist(),
        "embed_model": EMBED_MODEL,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=None))
    print(f"\n✓ Saved {len(examples)} examples → {OUTPUT_PATH}")
    print("  Run Jarvis now — it will load these automatically.")


if __name__ == "__main__":
    main()
