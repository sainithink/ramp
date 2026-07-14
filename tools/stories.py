"""Local Telugu story library tool for Jarvis."""
from __future__ import annotations

import json
import random
from pathlib import Path

STORIES_DIR = Path(__file__).parent.parent / "stories"

_stories: list[dict] | None = None


def _load_stories() -> list[dict]:
    global _stories
    if _stories is None:
        _stories = []
        for f in STORIES_DIR.glob("*.json"):
            _stories.extend(json.loads(f.read_text(encoding="utf-8")))
    return _stories


def get_story(category: str = "", title: str = "") -> str:
    stories = _load_stories()
    if not stories:
        return "క్షమించండి, నా దగ్గర ఇప్పుడు కథలు లేవు."

    # Filter by category or title if given
    pool = stories
    if title:
        pool = [s for s in stories if title.lower() in s["title"].lower()]
    elif category:
        pool = [s for s in stories if category.lower() in s["category"].lower()]

    if not pool:
        pool = stories

    story = random.choice(pool)
    return (
        f"**{story['title']}** ({story['category']})\n\n"
        f"{story['text']}\n\n"
        f"నీతి: {story['moral']}"
    )


def list_stories() -> str:
    stories = _load_stories()
    lines = [f"- {s['title']} ({s['category']})" for s in stories]
    return "నా దగ్గర ఉన్న కథలు:\n" + "\n".join(lines)
