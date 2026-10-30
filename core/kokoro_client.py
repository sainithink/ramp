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

    mp3_bytes = b""
    try:
        if _has_telugu(text):
            log.info("Telugu TTS via edge-tts")
            mp3_bytes = await _synthesize_telugu(text)
        else:
            log.info("English TTS via Kokoro")
            mp3_bytes = await asyncio.to_thread(_synthesize_english, text)
    except Exception as exc:
        # Telugu goes out to Microsoft's voice service, which refuses some
        # hosts outright — a datacenter address usually gets a 403. Kokoro is
        # local and always answers, so say it in the English voice rather than
        # return silence: a wrong accent beats an assistant that just stops.
        log.warning("TTS failed (%s) — falling back to the local voice", exc)
        try:
            mp3_bytes = await asyncio.to_thread(_synthesize_english, text)
        except Exception:
            log.exception("Local voice failed too")

    if not mp3_bytes:
        # Nothing was speakable at all: say so, rather than leaving the person
        # watching a robot that moved its mouth and made no sound.
        log.warning("Nothing to speak for %r", text[:60])
        try:
            mp3_bytes = await asyncio.to_thread(
                _synthesize_english, "Sorry, I could not say that out loud.")
        except Exception:
            log.exception("Could not synthesise the fallback line either")

    if mp3_bytes:
        await audio_queue.put(mp3_bytes)
