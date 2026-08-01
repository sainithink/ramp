"""Import Claude Code project chats into Saira's encrypted memory.

Reads the local session transcripts Claude Code writes under
~/.claude/projects/<project>/*.jsonl, pulls out the real back-and-forth, and
stores it with everything else Saira remembers. Nothing leaves the machine —
it goes into the same Fernet-encrypted memory.enc as spoken conversations.

    .venv/bin/python3.14 scripts/import_claude_chats.py            # preview
    .venv/bin/python3.14 scripts/import_claude_chats.py --write    # save
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import memory

TRANSCRIPT_DIR = (
    Path.home() / ".claude" / "projects"
    / "-Users-sainithink-Documents-learning-jarvis-code-share"
)

MAX_USER_LEN      = 400   # skip pasted logs/dumps
MAX_ASSISTANT_LEN = 300   # truncate replies; retrieval only needs the gist

# Bare commands that carry no information about the user worth recalling.
_NOISE = {
    "restart", "push", "push the code", "push it", "commit", "commit the code",
    "ok", "okay", "yes", "no", "y", "n", "go", "do it", "continue", "next",
    "thanks", "thank you", "stop", "wait", "test", "lets test", "run it",
}


# Transcripts can contain credentials the user pasted into chat. Those must
# never be copied into memory, where retrieval would later read them back out.
_SECRET_PATTERNS = (
    # sk-ant-api03-…, sk_… — hyphens and underscores appear inside the body
    re.compile(r"\bsk[-_][A-Za-z0-9_-]{16,}", re.I),          # Anthropic/OpenAI/ElevenLabs
    re.compile(r"\b(gh[pousr]|github_pat)_[A-Za-z0-9_]{16,}"),# GitHub
    re.compile(r"\bAKIA[0-9A-Z]{12,}"),                       # AWS access key
    re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),            # Slack
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]{20,}", re.I),   # bearer token
    re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}"),  # JWT
    re.compile(r"\b[0-9a-f]{32,}\b", re.I),                   # long hex secret
    # "<anything> key|token|secret|password [-:=] <value>" — bare "key" counts,
    # so "Anthropic key - …" is caught, not just "api key".
    re.compile(r"\b(key|secret|token|password|passwd|credential)s?"
               r"\s*[-:=]\s*\S{8,}", re.I),
)


def contains_secret(text: str) -> bool:
    return any(p.search(text) for p in _SECRET_PATTERNS)


def _is_noise(text: str) -> bool:
    t = text.strip().lower().rstrip(".!?")
    if t in _NOISE or len(t) < 4:
        return True
    # Slash commands, tool plumbing and injected blocks are not user speech
    return t.startswith(("/", "<local-command", "<command-name", "caveat:", "<system-reminder"))


def _iter_pairs(path: Path):
    """Yield (user_text, assistant_text) for one transcript file."""
    pending: str | None = None
    for line in path.read_text(errors="ignore").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue

        kind = row.get("type")
        content = row.get("message", {}).get("content")

        if kind == "user" and isinstance(content, str):
            if _is_noise(content) or len(content) > MAX_USER_LEN:
                pending = None
                continue
            pending = content.strip()

        elif kind == "assistant" and isinstance(content, list) and pending:
            text = " ".join(
                b.get("text", "") for b in content if b.get("type") == "text"
            ).strip()
            if text:
                yield pending, text[:MAX_ASSISTANT_LEN]
                pending = None


def collect() -> list[tuple[str, str]]:
    if not TRANSCRIPT_DIR.is_dir():
        print(f"No transcripts at {TRANSCRIPT_DIR}", file=sys.stderr)
        return []

    seen: set[str] = set()
    pairs: list[tuple[str, str]] = []
    skipped_secrets = 0
    for path in sorted(TRANSCRIPT_DIR.glob("*.jsonl"), key=os.path.getmtime):
        for user, assistant in _iter_pairs(path):
            key = user.lower()
            if key in seen:
                continue
            if contains_secret(user) or contains_secret(assistant):
                skipped_secrets += 1
                continue
            if not memory.is_worth_remembering(user, assistant):
                continue
            seen.add(key)
            pairs.append((user, assistant))
    if skipped_secrets:
        print(f"⚠  Skipped {skipped_secrets} exchange(s) containing credentials — "
              f"these were NOT imported.\n")
    return pairs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true", help="actually save to memory")
    args = ap.parse_args()

    pairs = collect()
    print(f"Found {len(pairs)} usable exchanges in {TRANSCRIPT_DIR.name}\n")
    for user, _ in pairs[:15]:
        print(f"  · {user[:90]}")
    if len(pairs) > 15:
        print(f"  … and {len(pairs) - 15} more")

    if not args.write:
        print("\nPreview only. Re-run with --write to save into memory.enc")
        return

    memory.init()
    before = len(memory._exchanges)
    for user, assistant in pairs:
        memory.save_exchange(user, assistant)
    after = len(memory._exchanges)
    print(f"\nMemory: {before} → {after} exchanges (+{after - before})")


if __name__ == "__main__":
    main()
