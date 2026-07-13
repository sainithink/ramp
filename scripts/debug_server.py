"""
Debug server — runs with full logging to debug.log
Run: .venv\Scripts\python scripts\debug_server.py
"""
import logging
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

log_path = os.path.join(os.path.dirname(__file__), "..", "debug.log")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    handlers=[
        logging.FileHandler(log_path, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
)

# Silence noisy libs
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("anthropic").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

import uvicorn
uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False, log_level="debug")
