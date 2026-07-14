"""
Local TTS via Kokoro — drop-in replacement for elevenlabs_client.
Generates MP3 audio entirely on-device, no API key needed.
"""
from __future__ import annotations

import asyncio
import io
import logging
from typing import AsyncIterator, Optional

import av
import numpy as np

log = logging.getLogger(__name__)

VOICE = "af_heart"   # warm female voice; see kokoro-onnx docs for full list
SAMPLE_RATE = 24000  # Kokoro native output rate

_kokoro: Optional[object] = None


def get_kokoro():
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro
        log.info("Loading Kokoro TTS model (first run downloads ~80 MB)…")
        _kokoro = Kokoro("kokoro-v1.0.int8.onnx", "voices-v1.0.bin")
        log.info("Kokoro TTS ready.")
    return _kokoro


def _pcm_to_mp3(samples: np.ndarray, sample_rate: int) -> bytes:
    """Encode float32 PCM → MP3 bytes using PyAV."""
    buf = io.BytesIO()
    container = av.open(buf, mode="w", format="mp3")
    stream = container.add_stream("libmp3lame", rate=sample_rate)
    stream.layout = "mono"

    pcm_int16 = (samples * 32767).clip(-32768, 32767).astype(np.int16)
    frame = av.AudioFrame.from_ndarray(pcm_int16.reshape(1, -1), format="s16", layout="mono")
    frame.sample_rate = sample_rate

    for packet in stream.encode(frame):
        container.mux(packet)
    for packet in stream.encode(None):
        container.mux(packet)
    container.close()

    return buf.getvalue()


def _synthesize(text: str) -> bytes:
    kokoro = get_kokoro()
    samples, sr = kokoro.create(text, voice=VOICE, speed=1.0, lang="en-us")
    return _pcm_to_mp3(np.array(samples, dtype=np.float32), sr)


async def synthesize_stream(
    text_iter: AsyncIterator[str],
    audio_queue: asyncio.Queue,
) -> None:
    """Collect all text, synthesize locally, push MP3 bytes to queue."""
    chunks: list[str] = []
    async for chunk in text_iter:
        chunks.append(chunk)

    text = "".join(chunks).strip()
    if not text:
        return

    try:
        mp3_bytes = await asyncio.to_thread(_synthesize, text)
        await audio_queue.put(mp3_bytes)
        log.debug("Kokoro synthesized %d bytes", len(mp3_bytes))
    except Exception as exc:
        log.exception("Kokoro TTS error: %s", exc)
