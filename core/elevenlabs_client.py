from __future__ import annotations

import asyncio
import base64
import json
import logging
import re
from typing import AsyncIterator

import websockets

from config import settings

log = logging.getLogger(__name__)

# streaming-input endpoint — responses are JSON with base64 audio field
_WS_URL = (
    f"wss://api.elevenlabs.io/v1/text-to-speech/{settings.elevenlabs_voice_id}"
    "/stream-input?model_id=eleven_turbo_v2"
)

_SENTENCE_END = re.compile(r"(?<=[.!?,])\s+")
_MIN_CHUNK_LEN = 8


async def synthesize_stream(
    text_iter: AsyncIterator[str],
    audio_queue: asyncio.Queue,
) -> None:
    headers = {"xi-api-key": settings.elevenlabs_api_key}

    try:
        async with websockets.connect(_WS_URL, extra_headers=headers) as ws:
            # Send initial BOS with voice settings
            await ws.send(json.dumps({
                "text": " ",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
                "xi_api_key": settings.elevenlabs_api_key,
            }))

            async def send_text():
                buffer = ""
                async for chunk in text_iter:
                    buffer += chunk
                    parts = _SENTENCE_END.split(buffer)
                    if len(parts) > 1:
                        to_send = " ".join(parts[:-1])
                        buffer = parts[-1]
                        if len(to_send) >= _MIN_CHUNK_LEN:
                            await ws.send(json.dumps({
                                "text": to_send + " ",
                                "try_trigger_generation": True,
                            }))
                # Flush remaining buffer
                if buffer.strip():
                    await ws.send(json.dumps({
                        "text": buffer + " ",
                        "try_trigger_generation": True,
                    }))
                # EOS signal
                await ws.send(json.dumps({"text": ""}))
                log.debug("ElevenLabs: text stream finished")

            async def receive_audio():
                try:
                    async for message in ws:
                        if isinstance(message, bytes):
                            # Raw binary frame (rare on this endpoint)
                            await audio_queue.put(message)
                        else:
                            try:
                                data = json.loads(message)
                            except Exception:
                                continue
                            audio_b64 = data.get("audio")
                            if audio_b64:
                                await audio_queue.put(base64.b64decode(audio_b64))
                            if data.get("isFinal"):
                                log.debug("ElevenLabs: isFinal received")
                                break
                except websockets.exceptions.ConnectionClosedOK:
                    log.debug("ElevenLabs: WS closed cleanly")
                except Exception as exc:
                    log.warning("ElevenLabs receive error: %s", exc)

            await asyncio.gather(send_text(), receive_audio())

    except Exception as exc:
        log.exception("ElevenLabs connection error: %s", exc)
