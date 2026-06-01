from functools import lru_cache

from pydantic import HttpUrl, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Base de datos
    DATABASE_URL: str
    TEST_DATABASE_URL: str = ""

    # JWT
    SECRET_KEY: SecretStr
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Cookie
    COOKIE_SECURE: bool = False

    # LLM externo
    LLM_API_KEY: SecretStr
    LLM_BASE_URL: HttpUrl
    LLM_MODEL: str = ""
    LLM_PROVIDER_TIMEOUT: int = 30

    # Bootstrap admin
    BOOTSTRAP_ADMIN_PASSWORD: SecretStr = SecretStr("")

    model_config = SettingsConfigDict(env_file=".env", extra="forbid")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
