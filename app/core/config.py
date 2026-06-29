from functools import lru_cache

from pydantic import HttpUrl, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


JWT_ALGORITHM = "HS256"


class Settings(BaseSettings):
    # Base de datos
    DATABASE_URL: str
    TEST_DATABASE_URL: str = ""

    # JWT
    SECRET_KEY: SecretStr
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

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, value: SecretStr) -> SecretStr:
        """Rechaza secrets vacíos o menores a 32 chars."""
        secret = value.get_secret_value()
        if not secret or len(secret) < 32:
            raise ValueError("SECRET_KEY debe tener al menos 32 caracteres")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
