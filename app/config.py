"""
Central configuration. Reads from environment / .env.
Import `settings` everywhere instead of calling os.getenv() ad-hoc.
"""
from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Core API keys (all optional -> features degrade gracefully) ---
    OPENAI_API_KEY: Optional[str] = None
    ASSEMBLYAI_API_KEY: Optional[str] = None
    FIRECRAWL_API_KEY: Optional[str] = None
    ZEP_API_KEY: Optional[str] = None

    # --- Database ---
    # SQLite now; swap to a postgres:// URL later with zero code changes.
    DATABASE_URL: str = "sqlite:///./thinkbooklm.db"

    # --- Vector DB (Milvus Lite) ---
    MILVUS_DATA_DIR: str = "./milvus_data"

    # --- Storage for generated audio, uploaded temp files ---
    OUTPUTS_DIR: str = "./outputs"

    # --- CORS ---
    # Comma-separated list in env, e.g. CORS_ORIGINS=https://myapp.lovable.app,http://localhost:5173
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # --- Session lifecycle ---
    SESSION_TTL_HOURS: int = 48          # sessions idle longer than this are eligible for cleanup
    CLEANUP_INTERVAL_MINUTES: int = 30   # how often the sweep runs

    # --- Uploads ---
    MAX_UPLOAD_SIZE_MB: int = 100
    ALLOWED_UPLOAD_EXTENSIONS: List[str] = [".pdf", ".txt", ".md", ".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"]

    # --- Job execution ---
    JOB_THREAD_POOL_SIZE: int = 4  # concurrent long-running jobs (transcription, TTS, etc.)

    # --- Auth ---
    JWT_SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"  # openssl rand -hex 32
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    VERIFICATION_TOKEN_EXPIRE_HOURS: int = 24
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
    REQUIRE_EMAIL_VERIFICATION_TO_LOGIN: bool = False  # if True, unverified users can't log in at all

    # --- Email (SMTP) ---
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: str = "ThinkbookLM <no-reply@thinkbooklm.local>"
    SMTP_USE_TLS: bool = True
    # Base URL of the frontend, used to build links inside emails, e.g.
    # {FRONTEND_URL}/verify-email?token=...
    FRONTEND_URL: str = "http://localhost:5173"

    @property
    def email_configured(self) -> bool:
        return bool(self.SMTP_HOST and self.SMTP_USER and self.SMTP_PASSWORD)

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def features(self) -> dict:
        """What's actually usable given the configured keys. Frontend should call /config."""
        return {
            "chat": bool(self.OPENAI_API_KEY),
            "document_upload": True,
            "audio_upload": bool(self.ASSEMBLYAI_API_KEY),
            "youtube": bool(self.ASSEMBLYAI_API_KEY),
            "web_scraping": bool(self.FIRECRAWL_API_KEY),
            "podcast_script": bool(self.OPENAI_API_KEY),
            "podcast_audio": True,  # Kokoro is local; verified at runtime, see /config
            "memory": bool(self.ZEP_API_KEY),
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
