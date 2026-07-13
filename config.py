import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    anthropic_api_key: str
    elevenlabs_api_key: str
    elevenlabs_voice_id: str = ""
    google_client_id: str = ""
    google_client_secret: str = ""
    google_token_json_path: str = "./google_token.json"
    host: str = "127.0.0.1"
    port: int = 8000

    def model_post_init(self, __context) -> None:
        if not self.elevenlabs_voice_id:
            raise ValueError(
                "ELEVENLABS_VOICE_ID is not set in .env. "
                "Find your voice ID at elevenlabs.io → Voices → click a voice → copy the ID."
            )


settings = Settings()
