"""
Local speech-to-text using faster-whisper.
Buffers WebM/Opus audio from the browser, decodes via PyAV, transcribes on PTT release.
No external API needed.
"""
from __future__ import annotations

import io
import logging
import os

import av
import numpy as np
from faster_whisper import WhisperModel

log = logging.getLogger(__name__)

# Two models, because the two jobs have very different requirements.
# The wake check re-runs every ~1.5s forever and only has to spot one word, so
# it gets the fastest model. Commands run once per turn and need accuracy.
# Measured on this machine for 3s of audio: tiny.en 0.24s, base.en 0.52s,
# small.en 2.0s — small.en took longer than the wake interval itself.
MODEL_SIZE      = os.environ.get("WHISPER_MODEL", "base.en")
WAKE_MODEL_SIZE = os.environ.get("WHISPER_WAKE_MODEL", "tiny.en")


def _load_model(size: str) -> WhisperModel:
    log.info("Loading Whisper model '%s'…", size)
    model = WhisperModel(size, device="cpu", compute_type="int8")
    log.info("Whisper model '%s' ready.", size)
    return model


_model: Optional[WhisperModel] = None
_wake_model: Optional[WhisperModel] = None


def get_model() -> WhisperModel:
    """Accurate model, used for actual commands."""
    global _model, _wake_model
    if _model is None:
        _model = _load_model(MODEL_SIZE)
    if _wake_model is None:
        _wake_model = _model if WAKE_MODEL_SIZE == MODEL_SIZE else _load_model(WAKE_MODEL_SIZE)
    return _model


def get_wake_model() -> WhisperModel:
    """Fast model, used for the constantly-running wake/barge-in checks."""
    if _wake_model is None:
        get_model()
    return _wake_model


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


def _as_float32(pcm: np.ndarray) -> np.ndarray:
    """Normalise int16 or float32 PCM to the float32 array faster-whisper wants."""
    if pcm.dtype == np.float32:
        return pcm
    return pcm.astype(np.float32) / 32768.0


def _transcribe_pcm(
    pcm: np.ndarray,
    vad: bool = True,
    language: str | None = None,
    fast: bool = False,
) -> str:
    """Transcribe 16 kHz mono PCM.

    `fast=True` uses the small wake model and greedy decoding — for the wake
    word and barge-in checks, which run constantly and only look for one word.
    """
    if pcm.size == 0:
        return ""
    # faster-whisper accepts a float32 array directly; the old code wrote a
    # temp WAV and read it back on every single call.
    audio = _as_float32(pcm)
    model = get_wake_model() if fast else get_model()
    kwargs: dict = {"beam_size": 1 if fast else 5, "task": "transcribe"}
    if language:
        kwargs["language"] = language
    if vad:
        kwargs["vad_filter"] = True
        kwargs["vad_parameters"] = {"threshold": 0.5, "min_silence_duration_ms": 500}
    segments, _ = model.transcribe(audio, **kwargs)
    text = " ".join(s.text for s in segments).strip()
    log.info("Whisper transcript%s: '%s'", " (fast)" if fast else "", text)
    return text


