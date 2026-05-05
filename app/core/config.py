from functools import lru_cache
from pydantic import ConfigDict, field_validator
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Configuración de la aplicación cargada desde variables de entorno."""
    # Base de datos
    DATABASE_URL: str
    TEST_DATABASE_URL: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Cookie
    COOKIE_SECURE: bool = False
    
    # LLM externo
    LLM_API_KEY: str
    LLM_BASE_URL: str
    LLM_MODEL: str

    # Bootstrap admin
    BOOTSTRAP_ADMIN_PASSWORD: str = ""
        
    model_config = ConfigDict(env_file=".env", extra="forbid")

    
@lru_cache
def get_settings() -> Settings:
    """Singleton de configuración — cacheado tras la primera llamada."""
    return Settings()