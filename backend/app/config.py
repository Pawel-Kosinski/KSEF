from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # .env nadpisuje .env.example (późniejszy plik wygrywa)
        env_file=(".env.example", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    database_url: str = "postgresql+asyncpg://vcfo:vcfo_secret@localhost:5432/wirtualny_cfo"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24
    encryption_master_key: str = ""
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
    ollama_timeout_sec: float = 45.0
    etl_classification_concurrency: int = 3

    # Virtual CFO Chat – Claude (Anthropic API)
    llm_provider: str = "claude"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    anthropic_max_tokens: int = 4096


def validate_settings(settings: Settings) -> None:
    """Walidacja konfiguracji przy starcie – błędy krytyczne w produkcji."""
    if settings.debug:
        return

    if not settings.encryption_master_key.strip():
        raise RuntimeError(
            "ENCRYPTION_MASTER_KEY jest wymagany gdy DEBUG=false. "
            'Wygeneruj: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        )

    if settings.jwt_secret_key in ("change-me-in-production", "change-me-in-production-use-openssl-rand-hex-32"):
        raise RuntimeError(
            "JWT_SECRET_KEY musi być zmieniony w produkcji (DEBUG=false)"
        )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    validate_settings(settings)
    return settings
