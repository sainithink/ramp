import asyncio
import io
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

import av
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from core.session import VoiceSession
from core.whisper_client import get_model, _transcribe_pcm, _decode_webm_to_pcm
from core.ollama_client import get_response
from core.kokoro_client import synthesize_stream, get_kokoro
from core.profile import load_profile
from core.memory import init as init_memory, save_exchange

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
log = logging.getLogger(__name__)

NOTEPAD_PATH = "./conversation_log.md"
SAMPLE_RATE  = 16000

# Silence detection via PCM RMS
SILENCE_THRESHOLD    = 0.02   # RMS below this = silence (raised to ignore background TV)
SILENCE_FRAMES_NEEDED = 15    # 15 × ~100ms = ~1.5s of silence to stop
MIN_SPEECH_FRAMES    = 4      # must hear speech before silence counts

# Wake-word detection
WAKE_CHECK_CHUNKS = 20        # check every 20 × 100ms = 2s
WAKE_WINDOW_SIZE  = 40        # 4s rolling window


def _log_exchange(user_text: str, saira_text: str) -> None:
    try:
        is_new = not os.path.exists(NOTEPAD_PATH)
        with open(NOTEPAD_PATH, "a", encoding="utf-8") as f:
            if is_new:
                f.write("# Saira Conversation Log\n\n")
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"---\n**[{ts}]**\n\n")
            f.write(f"**User:** {user_text}\n\n")
            f.write(f"**Saira:** {saira_text}\n\n")
    except Exception as exc:
        log.warning("Failed to write conversation log: %s", exc)


def _webm_to_pcm16k(webm_bytes: bytes) -> np.ndarray:
    """Decode WebM/Opus → 16kHz mono int16."""
    try:
        buf = io.BytesIO(webm_bytes)
        container = av.open(buf, format="webm")
        resampler = av.AudioResampler(format="s16", layout="mono", rate=SAMPLE_RATE)
        samples = []
        for frame in container.decode(audio=0):
            for rf in resampler.resample(frame):
                samples.append(rf.to_ndarray()[0])
        for rf in resampler.resample(None):
            samples.append(rf.to_ndarray()[0])
        return np.concatenate(samples) if samples else np.array([], dtype=np.int16)
    except Exception:
        return np.array([], dtype=np.int16)


def _contains_saira(text: str) -> bool:
    return "saira" in text.lower()


def _strip_wake_word(text: str) -> str:
    """Remove leading 'hey saira' or 'saira' from transcript."""
    import re
    return re.sub(r"^(hey\s+)?saira[,!.]*\s*", "", text, flags=re.IGNORECASE).strip()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Saira starting up…")
    load_profile()
    await asyncio.gather(
        asyncio.to_thread(get_model),
        asyncio.to_thread(get_kokoro),
        asyncio.to_thread(init_memory),
    )
    log.info("Saira ready.")
    yield
    log.info("Saira shutting down")


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.get("/favicon.ico")
async def favicon():
    from fastapi.responses import Response
    ico = bytes.fromhex(
        "00000100010001000000010020006804000016000000280000000100000002000000"
        "0100200000000000480000000000000000000000000000000000000000"
    )
    return Response(content=ico, media_type="image/x-icon")


@app.websocket("/ws/voice")
async def voice_endpoint(ws: WebSocket):
    await ws.accept()
    log.info(">>> WebSocket connected")
    session = VoiceSession(ws=ws)

    mode           = "wake"   # wake | command | processing
    listening_mode = "saira" # saira | always_on
    response_task  = None

    # Command-mode state (shared between receive loop and run_response)
    webm_header    = None
    command_raw    = []
    cmd_raw_chunks = []
    cmd_processed  = 0
    cmd_pcm_buf    = []
    silence_frames = 0
    speech_frames  = 0

    def _reset_command_state():
        nonlocal command_raw, cmd_raw_chunks, cmd_processed, cmd_pcm_buf, silence_frames, speech_frames
        command_raw    = []
        cmd_raw_chunks = [webm_header] if webm_header else []
        cmd_processed  = 0
        cmd_pcm_buf    = []
        silence_frames = 0
        speech_frames  = 0

    async def send_json(payload: dict):
        try:
            await ws.send_text(json.dumps(payload))
        except Exception:
            pass

    async def on_tool_call(name: str):
        await send_json({"type": "tool_call", "name": name})

    async def run_response(text: str):
        nonlocal mode
        log.info(">>> Running response for: '%s'", text)
        await send_json({"type": "transcript", "text": text})
        await send_json({"type": "status", "state": "thinking"})
        try:
            resp_chunks = []

            async def text_iter():
                async for delta in get_response(text, session.conversation_history, session, on_tool_call=on_tool_call):
                    resp_chunks.append(delta)
                    await send_json({"type": "response_chunk", "text": delta})
                    yield delta

            await synthesize_stream(text_iter(), session.audio_out_queue)
            full_reply = "".join(resp_chunks)
            _log_exchange(text, full_reply)
            await asyncio.to_thread(save_exchange, text, full_reply)
        except Exception as exc:
            log.exception("Pipeline error: %s", exc)
            await send_json({"type": "status", "state": "error"})
        finally:
            if listening_mode == "always_on":
                _reset_command_state()
                mode = "command"
                await send_json({"type": "status", "state": "always_on"})
                log.info(">>> Always-on: back to continuous listening")
            else:
                mode = "wake"
                await send_json({"type": "status", "state": "wake"})
                log.info(">>> Back to wake mode")

    async def transcribe_command(raw_chunks: list[bytes], header: bytes) -> None:
        nonlocal mode
        webm = b"".join([header] + raw_chunks)
        pcm = await asyncio.to_thread(_webm_to_pcm16k, webm)
        if pcm.size == 0:
            log.warning("Empty PCM after decode — skipping")
            if listening_mode == "always_on":
                _reset_command_state()
                mode = "command"
                await send_json({"type": "status", "state": "always_on"})
            else:
                mode = "wake"
                await send_json({"type": "status", "state": "wake"})
            return
        # Auto-detect language for commands (supports Telugu + English)
        text = await asyncio.to_thread(_transcribe_pcm, pcm, True, None)
        text = _strip_wake_word(text).strip()
        log.info("Command transcript: '%s'", text)
        if not text:
            if listening_mode == "always_on":
                _reset_command_state()
                mode = "command"
                await send_json({"type": "status", "state": "always_on"})
            else:
                mode = "wake"
                await send_json({"type": "status", "state": "wake"})
            return
        asyncio.create_task(run_response(text))

    async def receive_audio_task():
        nonlocal mode, response_task, webm_header, listening_mode
        nonlocal command_raw, cmd_raw_chunks, cmd_processed, cmd_pcm_buf, silence_frames, speech_frames

        wake_window      = []       # last WAKE_WINDOW_SIZE raw chunks
        wake_check_count = 0

        await send_json({"type": "status", "state": "wake"})

        try:
            while True:
                msg = await ws.receive()
                if msg["type"] == "websocket.disconnect":
                    break

                # ── Handle text control messages ───────────────────────
                text_msg = msg.get("text")
                if text_msg:
                    try:
                        ctrl = json.loads(text_msg)
                        if ctrl.get("type") == "set_listening_mode":
                            new_mode = ctrl.get("mode", "saira")
                            listening_mode = new_mode
                            log.info(">>> Listening mode changed to: %s", listening_mode)
                            if listening_mode == "always_on":
                                _reset_command_state()
                                mode = "command"
                                wake_window = []
                                wake_check_count = 0
                                await send_json({"type": "status", "state": "always_on"})
                            else:
                                mode = "wake"
                                wake_window = []
                                wake_check_count = 0
                                await send_json({"type": "status", "state": "wake"})
                    except Exception:
                        pass
                    continue

                chunk = msg.get("bytes")
                if not chunk:
                    continue

                # Save WebM header (first chunk ever) — skip it as audio data
                if webm_header is None:
                    webm_header = chunk
                    cmd_raw_chunks = [webm_header]
                    continue

                # ── PROCESSING: ignore incoming audio ──────────────────
                if mode == "processing":
                    continue

                # ── WAKE mode: rolling window + periodic keyword check ─
                if mode == "wake":
                    wake_window.append(chunk)
                    if len(wake_window) > WAKE_WINDOW_SIZE:
                        wake_window.pop(0)

                    wake_check_count += 1
                    if wake_check_count >= WAKE_CHECK_CHUNKS:
                        wake_check_count = 0
                        buf = b"".join([webm_header] + wake_window)
                        pcm = await asyncio.to_thread(_webm_to_pcm16k, buf)
                        if pcm.size > 0:
                            # English-locked, no VAD — finds "saira" reliably
                            text = await asyncio.to_thread(_transcribe_pcm, pcm, False, "en")
                            log.info("Wake window: '%s'", text)
                            if text and _contains_saira(text):
                                command = _strip_wake_word(text).strip()
                                if command:
                                    # Question already in wake phrase — respond immediately
                                    log.info(">>> Wake+command in one phrase: '%s'", command)
                                    mode = "processing"
                                    wake_window = []
                                    wake_check_count = 0
                                    await send_json({"type": "status", "state": "thinking"})
                                    asyncio.create_task(run_response(command))
                                else:
                                    # Just "Hey Saira" — wait for command
                                    log.info(">>> Wake word only — entering command mode")
                                    mode = "command"
                                    _reset_command_state()
                                    wake_window    = []
                                    wake_check_count = 0
                                    await send_json({"type": "status", "state": "listening"})

                # ── COMMAND mode: PCM RMS silence detection ─────────────
                elif mode == "command":
                    command_raw.append(chunk)
                    cmd_raw_chunks.append(chunk)

                    # Incremental decode for RMS
                    pcm = await asyncio.to_thread(_webm_to_pcm16k, b"".join(cmd_raw_chunks))
                    if pcm.size > cmd_processed:
                        new_pcm = pcm[cmd_processed:]
                        cmd_processed = pcm.size
                        cmd_pcm_buf.append(new_pcm)

                        rms = float(np.sqrt(np.mean(new_pcm.astype(np.float32) ** 2))) / 32768.0
                        if rms >= SILENCE_THRESHOLD:
                            speech_frames += 1
                            silence_frames = 0
                        elif speech_frames >= MIN_SPEECH_FRAMES:
                            silence_frames += 1

                        log.info("RMS=%.4f speech=%d silence=%d/%d", rms, speech_frames, silence_frames, SILENCE_FRAMES_NEEDED)

                        if silence_frames >= SILENCE_FRAMES_NEEDED and speech_frames >= MIN_SPEECH_FRAMES:
                            log.info(">>> Silence detected — transcribing %d cmd chunks", len(command_raw))
                            mode = "processing"
                            chunks_to_transcribe = command_raw[:]
                            hdr = webm_header
                            _reset_command_state()
                            await send_json({"type": "status", "state": "thinking"})
                            asyncio.create_task(transcribe_command(chunks_to_transcribe, hdr))

        except WebSocketDisconnect:
            pass
        except Exception as exc:
            log.exception("receive_audio_task error: %s", exc)

    async def send_audio_task():
        try:
            while True:
                chunk = await session.audio_out_queue.get()
                if chunk is None:
                    break
                await ws.send_bytes(chunk)
        except Exception as exc:
            log.exception("send_audio_task error: %s", exc)

    try:
        await asyncio.gather(receive_audio_task(), send_audio_task(), return_exceptions=True)
    finally:
        log.info(">>> WebSocket closed")
