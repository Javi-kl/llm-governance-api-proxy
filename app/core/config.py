from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación cargada desde variables de entorno."""

    # Base de datos
    DATABASE_URL: str
    TEST_DATABASE_URL: str = "sqlite:///:memory:"

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Cookie
    COOKIE_SECURE: bool = False

    # LLM externo
    LLM_API_KEY: str
    LLM_BASE_URL: str = "https://api.openai.com/v1"
    LLM_MODEL: str = "gpt4o"  # No verificado.

    # Bootstrap admin
    BOOTSTRAP_ADMIN_PASSWORD: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="forbid")


@lru_cache
def get_settings() -> Settings:
    """Singleton de configuración — cacheado tras la primera llamada."""
    return Settings()
