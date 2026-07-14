from __future__ import annotations

import asyncio
import logging
from typing import AsyncIterator, Callable, Awaitable, Optional

import anthropic

from config import settings
from tools import TOOL_DEFINITIONS, dispatch

log = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are Jarvis, a voice assistant. You talk like a real person — casual, warm, a little witty. "
    "Keep every reply to one or two short sentences max. No lists, no bullet points, no long explanations. "
    "If data comes back from a tool, pick the two or three most interesting numbers and mention just those. "
    "Never read out everything — summarise like you're telling a friend. "
    "Occasionally call the user sai or sir. "
    "If something fails, say so in one sentence and move on. Never show errors or technical details."
)

_client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


async def get_response(
    transcript: str,
    history: list,
    session,
    on_tool_call: Optional[Callable[[str], Awaitable[None]]] = None,
) -> AsyncIterator[str]:
    messages = list(history) + [{"role": "user", "content": transcript}]

    while True:
        is_tool_turn = False

        async with _client.messages.stream(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        ) as stream:
            # Stream text deltas immediately so ElevenLabs starts speaking ASAP.
            # If a tool_use block starts we know this isn't an end_turn — stop yielding.
            async for event in stream:
                if event.type == "content_block_start":
                    if getattr(event.content_block, "type", None) == "tool_use":
                        is_tool_turn = True
                elif event.type == "content_block_delta" and not is_tool_turn:
                    delta_text = getattr(event.delta, "text", None)
                    if delta_text:
                        yield delta_text

            final = await stream.get_final_message()

        stop_reason = final.stop_reason
        collected_content = final.content
        messages.append({"role": "assistant", "content": collected_content})

        if stop_reason == "end_turn":
            session.append_history("user", transcript)
            session.append_history("assistant", collected_content)
            return

        # tool_use turn
        tool_use_blocks = [b for b in collected_content if b.type == "tool_use"]
        if not tool_use_blocks:
            log.warning("stop_reason=tool_use but no tool_use blocks found")
            return

        async def run_tool(block):
            log.info("Tool call: %s %s", block.name, block.input)
            if on_tool_call:
                await on_tool_call(block.name)
            try:
                result = await dispatch(block.name, block.input)
            except Exception as exc:
                log.exception("Tool %s failed", block.name)
                result = f"Tool {block.name} failed: {exc}"
            return {
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": result,
            }

        tool_results = await asyncio.gather(*[run_tool(b) for b in tool_use_blocks])
        messages.append({"role": "user", "content": list(tool_results)})
