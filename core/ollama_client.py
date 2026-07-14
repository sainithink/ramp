"""Local LLM via Ollama with tool support."""
from __future__ import annotations

import json
import logging
from typing import AsyncIterator, Callable, Awaitable, Optional

import httpx
from core.profile import get_profile_text
from tools import TOOL_DEFINITIONS, dispatch

log = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2"

_BASE_PROMPT = (
    "You are Jarvis, a voice assistant. You talk like a real person — casual, warm, a little witty. "
    "Keep every reply to one or two short sentences max. No lists, no bullet points, no long explanations. "
    "When telling a story, read the full story text naturally — do not summarise it. "
    "If data comes back from a tool, pick the two or three most interesting things and mention just those. "
    "Never read out everything — summarise like you're telling a friend, EXCEPT for stories (read them fully). "
    "If you know the user's name, use it occasionally but not every time. "
    "If something fails, say so in one sentence and move on. Never show errors or technical details. "
    "IMPORTANT: If the user speaks or asks in Telugu, reply entirely in Telugu script. "
    "If the user speaks in English, reply in English."
)

# Convert TOOL_DEFINITIONS to Ollama format
_OLLAMA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": t["name"],
            "description": t["description"],
            "parameters": t["input_schema"],
        },
    }
    for t in TOOL_DEFINITIONS
]


def _build_system_prompt() -> str:
    profile = get_profile_text()
    if profile:
        return f"{_BASE_PROMPT}\n\n{profile}"
    return _BASE_PROMPT


async def get_response(
    transcript: str,
    history: list,
    session,
    on_tool_call: Optional[Callable[[str], Awaitable[None]]] = None,
) -> AsyncIterator[str]:
    messages = [{"role": "system", "content": _build_system_prompt()}]
    messages += list(history)
    messages.append({"role": "user", "content": transcript})

    full_response = []

    async with httpx.AsyncClient(timeout=120) as client:
        # Allow up to 3 tool call rounds
        for _ in range(3):
            payload = {
                "model": MODEL,
                "messages": messages,
                "tools": _OLLAMA_TOOLS,
                "stream": False,  # non-streaming for tool support
            }

            resp = await client.post(OLLAMA_URL, json=payload)
            resp.raise_for_status()
            data = resp.json()

            msg = data.get("message", {})
            tool_calls = msg.get("tool_calls", [])

            if tool_calls:
                # Execute each tool call
                messages.append({"role": "assistant", "content": "", "tool_calls": tool_calls})
                for tc in tool_calls:
                    fn = tc.get("function", {})
                    name = fn.get("name", "")
                    args = fn.get("arguments", {})
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except Exception:
                            args = {}
                    log.info("Tool call: %s(%s)", name, args)
                    if on_tool_call:
                        await on_tool_call(name)
                    result = await dispatch(name, args)
                    log.info("Tool result: %s", result[:200])
                    messages.append({
                        "role": "tool",
                        "content": result,
                    })
                # Loop: send tool results back to model
                continue

            # No tool calls — stream the final text response
            content = msg.get("content", "")
            if content:
                # Re-request with streaming for the final answer
                payload["stream"] = True
                payload["messages"] = messages
                async with client.stream("POST", OLLAMA_URL, json=payload) as streamed:
                    async for line in streamed.aiter_lines():
                        if not line:
                            continue
                        try:
                            chunk = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        delta = chunk.get("message", {}).get("content", "")
                        if delta:
                            full_response.append(delta)
                            yield delta
                        if chunk.get("done"):
                            break
            break

    full_text = "".join(full_response)
    session.append_history("user", transcript)
    session.append_history("assistant", full_text)
    log.info("Ollama response: '%s'", full_text[:120])
