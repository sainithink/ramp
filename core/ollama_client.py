"""Local LLM via Ollama with tool support."""
from __future__ import annotations

import json
import logging
from typing import AsyncIterator, Callable, Awaitable, Optional

import httpx
from core.profile import get_profile_text
from core.dpo_examples import get_few_shot_examples
from core.memory import get_relevant_context
from tools import TOOL_DEFINITIONS, dispatch

log = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2"

_BASE_PROMPT = (
    "You are Saira, a voice assistant. You talk like a real person — casual, warm, a little witty. "
    "Keep every reply to one or two short sentences max. No lists, no bullet points, no long explanations. "
    "Answer questions directly with facts. "
    "If you don't know something or are not sure, say exactly 'I don't have that information' — never guess, never make up facts, never call a tool as a substitute for not knowing. "
    "TOOL USE RULES — follow these strictly: "
    "  • get_story: ONLY when the user says 'tell me a story', 'కథ చెప్పు', or explicitly asks for a story. NEVER for any other question. "
    "  • get_weather: ONLY when the user asks about weather. "
    "  • list_stories: ONLY when the user asks what stories are available. "
    "  • For ALL other questions (visa, jobs, health, facts, how-to, etc.) — answer directly WITHOUT calling any tool. "
    "When telling a story, read the full story text naturally — do not summarise it. "
    "If data comes back from a tool, pick the two or three most interesting things and mention just those. "
    "If you know the user's name, use it occasionally but not every time. "
    "If something fails, say so in one sentence and move on. Never show errors or technical details. "
    "IMPORTANT: If the user speaks or asks in Telugu, reply entirely in Telugu script. "
    "If the user speaks in English, reply in English."
)

_STORY_KEYWORDS = {
    "story", "stories", "కథ", "కథలు", "కథ చెప్పు", "కథ వినాలి", "tell me a", "narrate",
    "panchatantra", "పంచతంత్ర", "tenali", "తెనాలి",
}

_WEATHER_KEYWORDS = {
    "weather", "temperature", "forecast", "rain", "sunny", "cloudy", "humid",
    "hot", "cold", "climate", "వాతావరణం", "వర్షం", "ఉష్ణోగ్రత",
}

def _tools_for_query(query: str) -> list:
    """Only pass tools to LLM when the query explicitly asks for them."""
    q = query.lower()
    wants_story   = any(kw in q for kw in _STORY_KEYWORDS)
    wants_weather = any(kw in q for kw in _WEATHER_KEYWORDS)
    allowed = set()
    if wants_story:
        allowed |= {"get_story", "list_stories"}
    if wants_weather:
        allowed.add("get_weather")
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        }
        for t in TOOL_DEFINITIONS
        if t["name"] in allowed
    ]


def _build_system_prompt(user_query: str = "") -> str:
    parts = [_BASE_PROMPT]
    profile = get_profile_text()
    if profile:
        parts.append(profile)
    if user_query:
        memory = get_relevant_context(user_query)
        if memory:
            parts.append(memory)
        few_shot = get_few_shot_examples(user_query)
        if few_shot:
            parts.append(few_shot)
    return "\n\n".join(parts)


async def get_response(
    transcript: str,
    history: list,
    session,
    on_tool_call: Optional[Callable[[str], Awaitable[None]]] = None,
) -> AsyncIterator[str]:
    messages = [{"role": "system", "content": _build_system_prompt(transcript)}]
    messages += list(history)
    messages.append({"role": "user", "content": transcript})

    full_response = []

    async with httpx.AsyncClient(timeout=120) as client:
        # Allow up to 3 tool call rounds
        for _ in range(3):
            payload = {
                "model": MODEL,
                "messages": messages,
                "tools": _tools_for_query(transcript),
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
