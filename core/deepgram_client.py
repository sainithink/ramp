from __future__ import annotations

import asyncio
import logging
from typing import Callable, Awaitable, Optional

from deepgram import Deepgram

from config import settings

log = logging.getLogger(__name__)


class DeepgramStreamer:
    def __init__(self):
        self._dg = Deepgram(settings.deepgram_api_key)
        self._connection = None
        self._last_transcript: str = ""

    async def open(self, on_final_transcript: Callable[[str], Awaitable[None]]) -> None:
        if self._connection is not None:
            await self.close()

        self._last_transcript = ""

        async def _on_transcript(data):
            try:
                alts = data.get("channel", {}).get("alternatives", [{}])
                transcript = alts[0].get("transcript", "").strip()
                is_final = data.get("is_final", False)
                speech_final = data.get("speech_final", False)

                if not transcript:
                    return

                log.debug("Deepgram result: is_final=%s speech_final=%s text='%s'",
                          is_final, speech_final, transcript)

                # Trigger on speech_final (pause detected) OR is_final (stream closing)
                if speech_final or is_final:
                    self._last_transcript = transcript
                    await on_final_transcript(transcript)
            except Exception as exc:
                log.error("Transcript handler error: %s", exc)

        self._connection = await self._dg.transcription.live({
            "model": "nova-2",
            "language": "en-US",
            # No encoding/sample_rate — let Deepgram auto-detect WebM/Opus from MediaRecorder
            "interim_results": True,
            "endpointing": 300,
        })

        self._connection.registerHandler(
            self._connection.event.TRANSCRIPT_RECEIVED,
            _on_transcript,
        )
        self._connection.registerHandler(
            self._connection.event.ERROR,
            lambda e: log.error("Deepgram error: %s", e),
        )

        log.info("Deepgram connection opened")

    def send_audio(self, data: bytes) -> None:
        if self._connection is not None:
            self._connection.send(data)

    async def close(self) -> None:
        if self._connection is not None:
            try:
                await self._connection.finish()
            except Exception as exc:
                log.warning("Deepgram close error: %s", exc)
            finally:
                self._connection = None
