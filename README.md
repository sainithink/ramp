# J.A.R.V.I.S — Local Voice AI Assistant

A fully local voice assistant built with FastAPI. No cloud APIs or API keys required — everything runs on your machine.

## Stack
| Component | Technology |
|---|---|
| Speech-to-text | faster-whisper (Whisper `base` model, CPU) |
| AI brain | Ollama + `llama3.2` |
| Text-to-speech | Kokoro ONNX (`af_heart` voice) |
| Weather data | Open-Meteo (free public API, no key) |
| Frontend | React + Vite + Tailwind, with [Animate UI](https://animate-ui.com) primitives |
| Accounts | SQLAlchemy + SQLite, per-user encrypted memory |

## Setup

### 1. Python 3.8+
```bash
python -m venv .venv
source .venv/bin/activate   # Mac/Linux
# .venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

### 2. Ollama (local LLM)
```bash
brew install ollama          # Mac
ollama serve                 # start the service
ollama pull llama3.2         # download the model (~2 GB)
```

### 3. Kokoro model files
Download into the project root:
```bash
wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx
wget https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin
```

### 4. Frontend
The pages are a React app in `web/` that builds into `static/build`. The build
is committed, so this is only needed after changing anything under `web/`:

```bash
nvm use 22            # Vite 8 needs Node 22
cd web && npm install && npm run build
```

See [web/README.md](web/README.md) for the dev server and the Animate UI setup.

### 5. Run
```bash
.venv/bin/python -m uvicorn main:app --port 3001
# Open http://localhost:3001
```

The first account to register becomes the admin. Models load automatically on
first startup; Whisper and Kokoro cache to `~/.cache/huggingface/` after the
first run.
