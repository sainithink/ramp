"""
Local speech-to-text using faster-whisper.
Buffers WebM/Opus audio from the browser, decodes via PyAV, transcribes on PTT release.
No external API needed.
"""
from __future__ import annotations

import asyncio
import io
import logging
import os
import tempfile
from typing import Callable, Awaitable, Optional

import av
import numpy as np
from faster_whisper import WhisperModel

log = logging.getLogger(__name__)

MODEL_SIZE = os.environ.get("WHISPER_MODEL", "small")


def _load_model() -> WhisperModel:
    log.info("Loading Whisper model '%s' (first run downloads ~150 MB)…", MODEL_SIZE)
    model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
    log.info("Whisper model ready.")
    return model


# Load once at import time so the model is warm before the first request.
_model: Optional[WhisperModel] = None


def get_model() -> WhisperModel:
    global _model
    if _model is None:
        _model = _load_model()
    return _model


def _decode_webm_to_pcm(webm_bytes: bytes) -> np.ndarray:
    """Decode WebM/Opus bytes → 16 kHz mono float32 PCM array."""
    buf = io.BytesIO(webm_bytes)
    container = av.open(buf, format="webm")
    resampler = av.AudioResampler(format="fltp", layout="mono", rate=16000)

    samples: list[np.ndarray] = []
    for frame in container.decode(audio=0):
        for rf in resampler.resample(frame):
            samples.append(rf.to_ndarray()[0])

    # Flush resampler
    for rf in resampler.resample(None):
        samples.append(rf.to_ndarray()[0])

    if not samples:
        return np.array([], dtype=np.float32)
    return np.concatenate(samples)


def _pcm_to_wav(pcm: np.ndarray) -> str:
    """Write float32 or int16 PCM → temp WAV file, return path."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_path = f.name
    container = av.open(wav_path, mode="w")
    stream = container.add_stream("pcm_s16le", rate=16000)
    stream.layout = "mono"
    if pcm.dtype == np.float32:
        pcm = (pcm * 32767).clip(-32768, 32767).astype(np.int16)
    frame = av.AudioFrame.from_ndarray(pcm.reshape(1, -1), format="s16", layout="mono")
    frame.sample_rate = 16000
    for packet in stream.encode(frame):
        container.mux(packet)
    for packet in stream.encode(None):
        container.mux(packet)
    container.close()
    return wav_path


def _transcribe_pcm(pcm: np.ndarray, vad: bool = True, language: str | None = None) -> str:
    if pcm.size == 0:
        return ""
    wav_path = _pcm_to_wav(pcm)
    try:
        model = get_model()
        kwargs: dict = {"beam_size": 5, "task": "transcribe"}
        if language:
            kwargs["language"] = language
        if vad:
            kwargs["vad_filter"] = True
            kwargs["vad_parameters"] = {"threshold": 0.3, "min_silence_duration_ms": 300}
        segments, _ = model.transcribe(wav_path, **kwargs)
        text = " ".join(s.text for s in segments).strip()
        log.info("Whisper transcript: '%s'", text)
        return text
    finally:
        os.unlink(wav_path)


def _transcribe(webm_bytes: bytes) -> str:
    pcm = _decode_webm_to_pcm(webm_bytes)
    return _transcribe_pcm(pcm)


class WhisperStreamer:
    """Drop-in replacement for DeepgramStreamer using local Whisper."""

    def __init__(self):
        self._chunks: list[bytes] = []
        self._on_final_transcript: Optional[Callable[[str], Awaitable[None]]] = None

    async def open(self, on_final_transcript: Callable[[str], Awaitable[None]]) -> None:
        self._on_final_transcript = on_final_transcript
        self._chunks = []

    def send_audio(self, data: bytes) -> None:
        self._chunks.append(data)

    async def close(self) -> None:
        if not self._chunks or self._on_final_transcript is None:
            self._chunks = []
            return
        webm_bytes = b"".join(self._chunks)
        self._chunks = []
        try:
            text = await asyncio.to_thread(_transcribe, webm_bytes)
            if text:
                await self._on_final_transcript(text)
        except Exception as exc:
            log.exception("Whisper transcription error: %s", exc)

    async def close_from_pcm(self, pcm: np.ndarray) -> None:
        """Transcribe directly from a PCM array (int16, 16kHz) — skips WebM decode."""
        if self._on_final_transcript is None:
            return
        try:
            text = await asyncio.to_thread(_transcribe_pcm, pcm)
            if text:
                await self._on_final_transcript(text)
        except Exception as exc:
            log.exception("Whisper PCM transcription error: %s", exc)
