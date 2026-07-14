"""
Local LLM via Ollama — drop-in replacement for claude_client.
Streams text from a locally running Ollama model.
"""
from __future__ import annotations

import json
import logging
from typing import AsyncIterator, Callable, Awaitable, Optional

import httpx

log = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2"

SYSTEM_PROMPT = (
    "You are Jarvis, a voice assistant. You talk like a real person — casual, warm, a little witty. "
    "Keep every reply to one or two short sentences max. No lists, no bullet points, no long explanations. "
    "If data comes back from a tool, pick the two or three most interesting numbers and mention just those. "
    "Never read out everything — summarise like you're telling a friend. "
    "Occasionally call the user Lahari or ma'am, never sir. "
    "If something fails, say so in one sentence and move on. Never show errors or technical details."
)


async def get_response(
    transcript: str,
    history: list,
    session,
    on_tool_call: Optional[Callable[[str], Awaitable[None]]] = None,
) -> AsyncIterator[str]:
    """Stream a response from the local Ollama model."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages += list(history)
    messages.append({"role": "user", "content": transcript})

    payload = {
        "model": MODEL,
        "messages": messages,
        "stream": True,
    }

    full_response = []

    async with httpx.AsyncClient(timeout=60) as client:
        async with client.stream("POST", OLLAMA_URL, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                delta = data.get("message", {}).get("content", "")
                if delta:
                    full_response.append(delta)
                    yield delta

                if data.get("done"):
                    break

    full_text = "".join(full_response)
    session.append_history("user", transcript)
    session.append_history("assistant", full_text)
    log.info("Ollama response: '%s'", full_text[:120])
