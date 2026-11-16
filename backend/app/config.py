from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    app_env: str = 'development'
    database_url: str = ''
    test_database_url: str = ''
    allowed_origins: list[str] = ['http://127.0.0.1:5173', 'http://localhost:5173']


@lru_cache
def get_settings() -> Settings:
    return Settings()
