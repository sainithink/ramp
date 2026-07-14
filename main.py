import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from core.session import VoiceSession
from core.whisper_client import WhisperStreamer, get_model
from core.ollama_client import get_response
from core.kokoro_client import synthesize_stream, get_kokoro

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
log = logging.getLogger(__name__)

NOTEPAD_PATH = "./conversation_log.md"


def _log_exchange(user_text: str, jarvis_text: str) -> None:
    """Append a dialogue exchange to the conversation notepad."""
    try:
        is_new = not os.path.exists(NOTEPAD_PATH)
        with open(NOTEPAD_PATH, "a", encoding="utf-8") as f:
            if is_new:
                f.write("# Jarvis Conversation Log\n\n")
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"---\n**[{ts}]**\n\n")
            f.write(f"**Lahari:** {user_text}\n\n")
            f.write(f"**Jarvis:** {jarvis_text}\n\n")
    except Exception as exc:
        log.warning("Failed to write conversation log: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Jarvis starting up — pre-loading models…")
    await asyncio.gather(
        asyncio.to_thread(get_model),
        asyncio.to_thread(get_kokoro),
    )
    log.info("Jarvis ready.")
    yield
    log.info("Jarvis shutting down")


app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.get("/favicon.ico")
async def favicon():
    from fastapi.responses import Response
    # Minimal 1x1 transparent ICO
    ico = bytes.fromhex(
        "00000100010001000000010020006804000016000000280000000100000002000000"
        "0100200000000000480000000000000000000000000000000000000000"
    )
    return Response(content=ico, media_type="image/x-icon")


@app.get("/test-pipeline")
async def test_pipeline():
    """Hit this in browser to test Claude + ElevenLabs without microphone."""
    from fastapi.responses import StreamingResponse
    import io

    audio_queue = asyncio.Queue()

    async def fake_text():
        yield "Hello, I am Jarvis. The pipeline is working correctly."

    await synthesize_stream(fake_text(), audio_queue)

    chunks = []
    while not audio_queue.empty():
        chunks.append(audio_queue.get_nowait())

    if not chunks:
        from fastapi.responses import JSONResponse
        return JSONResponse({"error": "ElevenLabs returned no audio"}, status_code=500)

    audio_bytes = b"".join(chunks)
    return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/mpeg",
                             headers={"Content-Disposition": "inline; filename=test.mp3"})


@app.websocket("/ws/voice")
async def voice_endpoint(ws: WebSocket):
    await ws.accept()
    log.info(">>> WebSocket client connected")
    session = VoiceSession(ws=ws)
    streamer = WhisperStreamer()

    async def send_json(payload: dict):
        try:
            await ws.send_text(json.dumps(payload))
        except Exception:
            pass

    async def on_tool_call(tool_name: str):
        log.info(">>> Tool call: %s", tool_name)
        await send_json({"type": "tool_call", "name": tool_name})

    async def on_final_transcript(text: str):
        if not text.strip():
            return
        log.info(">>> TRANSCRIPT RECEIVED: '%s'", text)
        await send_json({"type": "transcript", "text": text})
        await send_json({"type": "status", "state": "thinking"})
        session.is_speaking = True

        try:
            log.info(">>> Calling Claude...")
            response_text = []

            async def text_iter():
                async for delta in get_response(
                    text,
                    session.conversation_history,
                    session,
                    on_tool_call=on_tool_call,
                ):
                    response_text.append(delta)
                    await send_json({"type": "response_chunk", "text": delta})
                    yield delta
                if response_text:
                    log.info(">>> Claude full response: '%s'", "".join(response_text)[:120])

            log.info(">>> Starting ElevenLabs TTS stream...")
            await synthesize_stream(text_iter(), session.audio_out_queue)
            full_response = "".join(response_text)
            log.info(">>> TTS complete.")
            _log_exchange(text, full_response)

        except Exception as exc:
            log.exception(">>> Pipeline ERROR: %s", exc)
            await send_json({"type": "status", "state": "error"})
        finally:
            session.is_speaking = False
            await send_json({"type": "status", "state": "listening"})

    async def receive_audio_task():
        await send_json({"type": "status", "state": "listening"})
        audio_chunks_sent = 0
        try:
            while True:
                message = await ws.receive()
                if message["type"] == "websocket.disconnect":
                    log.info(">>> WebSocket disconnected")
                    break
                if message.get("bytes"):
                    streamer.send_audio(message["bytes"])
                    audio_chunks_sent += 1
                    if audio_chunks_sent % 20 == 0:
                        log.debug(">>> Audio chunks buffered: %d", audio_chunks_sent)
                elif message.get("text"):
                    control = json.loads(message["text"])
                    msg_type = control.get("type")
                    log.info(">>> Control message: %s", msg_type)
                    if msg_type == "start":
                        audio_chunks_sent = 0
                        log.info(">>> PTT start — opening Whisper buffer")
                        await streamer.open(on_final_transcript)
                        await send_json({"type": "status", "state": "listening"})
                    elif msg_type == "stop":
                        log.info(">>> PTT stop — transcribing %d audio chunks", audio_chunks_sent)
                        await send_json({"type": "status", "state": "thinking"})
                        await streamer.close()
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
        await asyncio.gather(
            receive_audio_task(),
            send_audio_task(),
            return_exceptions=True,
        )
    finally:
        await streamer.close()
        log.info(">>> WebSocket session closed")
