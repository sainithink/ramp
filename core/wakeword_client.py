"""
Wake word detection using OpenWakeWord (hey_saira model).
Processes raw 16kHz PCM chunks from the browser audio stream.
"""
from __future__ import annotations

import logging
import numpy as np

log = logging.getLogger(__name__)

CHUNK_SAMPLES = 1280   # 80ms at 16kHz — OWW requirement
THRESHOLD     = 0.3    # confidence threshold for detection

_oww = None


def get_oww():
    global _oww
    if _oww is None:
        from openwakeword.model import Model
        log.info("Loading hey_saira wake word model…")
        _oww = Model(wakeword_models=["hey_saira"], inference_framework="onnx")
        log.info("Wake word model ready.")
    return _oww


class WakeWordDetector:
    """
    Feed 16kHz mono int16 PCM bytes in chunks.
    Returns True from process() when 'hey saira' is detected.
    """

    def __init__(self):
        self._buffer = np.array([], dtype=np.int16)

    def reset(self):
        self._buffer = np.array([], dtype=np.int16)
        get_oww().reset()

    def process(self, pcm_int16: np.ndarray) -> bool:
        self._buffer = np.concatenate([self._buffer, pcm_int16])
        oww = get_oww()
        detected = False

        while len(self._buffer) >= CHUNK_SAMPLES:
            chunk = self._buffer[:CHUNK_SAMPLES]
            self._buffer = self._buffer[CHUNK_SAMPLES:]

            chunk_f32 = chunk.astype(np.float32) / 32768.0
            scores = oww.predict(chunk_f32)

            score = scores.get("hey_saira", 0.0)
            if score > 0.05:
                log.info("OWW score=%.3f (threshold=%.2f)", score, THRESHOLD)
            if score >= THRESHOLD:
                log.info("Wake word detected (score=%.2f)", score)
                detected = True
                self.reset()

        return detected
