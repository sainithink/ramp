# J.A.R.V.I.S — Local Voice AI Assistant

A local voice assistant built with FastAPI, Deepgram STT, Claude AI, and ElevenLabs TTS.
Push-to-talk (or double-clap) to speak, Jarvis answers out loud.

## Features
- Voice-activated with Push-to-Talk button or double-clap
- Powered by Claude Haiku (fast + cheap)
- Tools: weather lookup, Google Calendar (read & create events)
- Sci-fi HUD frontend

## Setup

### 1. Python 3.8+
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
```

### 2. Environment variables
```bash
cp .env.example .env
# Edit .env and fill in all your API keys
```

### 3. Google Calendar
```bash
python scripts/auth_google.py
# Opens a browser OAuth flow — saves google_token.json
```

### 4. Run
```bash
python scripts/debug_server.py
# Then open http://localhost:8000
```

## API Keys needed
| Service | Purpose | Link |
|---|---|---|
| Deepgram | Speech-to-text | console.deepgram.com |
| Anthropic | Claude AI brain | console.anthropic.com |
| ElevenLabs | Voice synthesis | elevenlabs.io |
| Google Cloud | Calendar access | console.cloud.google.com |
