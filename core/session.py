import asyncio
from dataclasses import dataclass, field
from fastapi import WebSocket


@dataclass
class VoiceSession:
    ws: WebSocket
    transcript_buffer: str = ""
    audio_out_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    is_speaking: bool = False
    conversation_history: list = field(default_factory=list)

    def append_history(self, role: str, content) -> None:
        self.conversation_history.append({"role": role, "content": content})
        # Keep last 10 exchanges (20 messages)
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]
