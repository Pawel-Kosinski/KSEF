from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.example"),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    database_url: str = "postgresql+asyncpg://vcfo:vcfo_secret@localhost:5432/wirtualny_cfo"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    app_name: str = "Wirtualny CFO"
    debug: bool = False

    # KSeF API 2.0 – środowisko testowe domyślnie (zgodnie z planem projektu)
    ksef_base_url: str = "https://api-test.ksef.mf.gov.pl/api/v2"
    ksef_nip: str = ""
    ksef_token: str = ""
    ksef_auth_poll_interval_sec: float = 1.0
    ksef_auth_poll_max_attempts: int = 60
    ksef_export_poll_interval_sec: float = 2.0
    ksef_export_poll_max_attempts: int = 120

    # Ollama – lokalny SLM (Faza 3)
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:7b"


@lru_cache
def get_settings() -> Settings:
    return Settings()
