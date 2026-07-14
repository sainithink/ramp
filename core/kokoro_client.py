"""
TTS — Kokoro ONNX for English, edge-tts for Telugu (and other languages).
"""
from __future__ import annotations

import asyncio
import io
import logging
import re
import tempfile
import os
from typing import AsyncIterator, Optional

import av
import numpy as np

log = logging.getLogger(__name__)

KOKORO_VOICE   = "af_heart"
TELUGU_VOICE   = "te-IN-ShrutiNeural"   # edge-tts Telugu female
SAMPLE_RATE    = 24000

_kokoro: Optional[object] = None


def get_kokoro():
    global _kokoro
    if _kokoro is None:
        from kokoro_onnx import Kokoro
        log.info("Loading Kokoro TTS model…")
        _kokoro = Kokoro("kokoro-v1.0.int8.onnx", "voices-v1.0.bin")
        log.info("Kokoro TTS ready.")
    return _kokoro


def _has_telugu(text: str) -> bool:
    """Return True if text contains Telugu Unicode characters."""
    return bool(re.search(r'[ఀ-౿]', text))


def _ascii_safe(text: str) -> str:
    cleaned = re.sub(r'[^\x00-\x7F]+', ' ', text)
    return ' '.join(cleaned.split())


def _pcm_to_mp3(samples: np.ndarray, sample_rate: int) -> bytes:
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


def _synthesize_english(text: str) -> bytes:
    safe = _ascii_safe(text)
    if not safe:
        return b""
    kokoro = get_kokoro()
    samples, sr = kokoro.create(safe, voice=KOKORO_VOICE, speed=1.0, lang="en-us")
    return _pcm_to_mp3(np.array(samples, dtype=np.float32), sr)


async def _synthesize_telugu(text: str) -> bytes:
    """Use edge-tts for Telugu — returns MP3 bytes."""
    import edge_tts
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        tmp = f.name
    try:
        communicate = edge_tts.Communicate(text, TELUGU_VOICE)
        await communicate.save(tmp)
        with open(tmp, "rb") as f:
            return f.read()
    finally:
        os.unlink(tmp)


async def synthesize_stream(
    text_iter: AsyncIterator[str],
    audio_queue: asyncio.Queue,
) -> None:
    chunks: list[str] = []
    async for chunk in text_iter:
        chunks.append(chunk)

    text = "".join(chunks).strip()
    if not text:
        return

    try:
        if _has_telugu(text):
            log.info("Telugu TTS via edge-tts")
            mp3_bytes = await _synthesize_telugu(text)
        else:
            log.info("English TTS via Kokoro")
            mp3_bytes = await asyncio.to_thread(_synthesize_english, text)

        if mp3_bytes:
            await audio_queue.put(mp3_bytes)
    except Exception as exc:
        log.exception("TTS error: %s", exc)
