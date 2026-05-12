from functools import lru_cache

from pydantic import HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuración de la aplicación cargada desde variables de entorno."""

    # Base de datos
    DATABASE_URL: str

    # JWT
    SECRET_KEY: SecretStr
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Cookie
    COOKIE_SECURE: bool = False

    # LLM externo
    LLM_API_KEY: SecretStr
    LLM_BASE_URL: HttpUrl
    LLM_MODEL: str = "gpt4o"  # No verificado.

    # Bootstrap admin
    BOOTSTRAP_ADMIN_PASSWORD: SecretStr = SecretStr("")

    model_config = SettingsConfigDict(env_file=".env", extra="forbid")


@lru_cache
def get_settings() -> Settings:
    """Cacheado tras la primera llamada."""
    return Settings() # type: ignore[call-arg]
