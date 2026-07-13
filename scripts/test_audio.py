"""
Run this to diagnose audio pipeline issues:
    .venv\Scripts\python scripts\test_audio.py

It tests ElevenLabs TTS directly and saves the output to test_output.mp3
so you can verify audio is being generated without needing the full server.
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.elevenlabs_client import synthesize_stream


async def fake_text_iter():
    yield "Hello, I am Jarvis. Your systems are online and ready."


async def main():
    print("Testing ElevenLabs TTS connection...")
    audio_queue = asyncio.Queue()

    try:
        await synthesize_stream(fake_text_iter(), audio_queue)
    except Exception as e:
        print(f"ERROR connecting to ElevenLabs: {e}")
        return

    chunks = []
    while not audio_queue.empty():
        chunks.append(audio_queue.get_nowait())

    if not chunks:
        print("FAIL: ElevenLabs returned zero audio bytes.")
        print("  - Check ELEVENLABS_API_KEY and ELEVENLABS_VOICE_ID in .env")
        print("  - Check your ElevenLabs account has remaining credits")
        return

    total = sum(len(c) for c in chunks)
    print(f"OK: Received {len(chunks)} audio chunks, {total} bytes total")

    out_path = os.path.join(os.path.dirname(__file__), "..", "test_output.mp3")
    with open(out_path, "wb") as f:
        for chunk in chunks:
            f.write(chunk)
    print(f"Saved to: {os.path.abspath(out_path)}")
    print("Open test_output.mp3 to verify Jarvis's voice sounds correct.")


asyncio.run(main())
