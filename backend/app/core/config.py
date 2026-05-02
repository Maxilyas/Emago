"""
app/core/config.py
Paramètres centralisés — toutes les valeurs sensibles viennent de l'environnement.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    APP_NAME: str = "Emago"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    SECRET_KEY: str  # obligatoire

    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"

    # URLs autorisées en production (ex: "https://emago.example.com")
    # Séparées par des virgules dans la variable d'environnement CORS_ORIGINS
    CORS_ORIGINS: list[str] = []

    RESOURCE_TICK_SECONDS: int = 60
    BUILD_QUEUE_MAX: int = 5
    FLEET_SPEED_BASE: float = 1.0
    RANKING_RECALC_MINUTES: int = 10
    FORGE_DURATION_HOURS: int = 8


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Alias direct pour les imports Alembic (env.py)
settings = get_settings()
