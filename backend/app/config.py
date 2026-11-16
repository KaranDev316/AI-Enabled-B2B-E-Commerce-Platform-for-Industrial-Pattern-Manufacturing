from functools import lru_cache
import json
from pathlib import Path
from typing import Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = Path(__file__).resolve().parents[2]

ENV_FILES = (
    BACKEND_DIR / '.env',
    ROOT_DIR / '.env',
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILES,
        env_file_encoding='utf-8',
        extra='ignore',
    )

    app_env: str = 'development'
    database_url: str = ''
    test_database_url: str = ''
    allowed_origins: Union[list[str], str] = [
        'http://127.0.0.1:5173',
        'http://localhost:5173',
        'http://127.0.0.1:8000',
        'http://localhost:8000',
    ]
    session_cookie_name: str = 'kpc_session'
    session_ttl_seconds: int = 86400
    session_secure_cookie: bool = False

    # Private Storage configuration (Supabase with local fallback)
    supabase_url: str = ''
    supabase_service_role_key: str = ''
    supabase_storage_bucket: str = 'kpc-private-files'
    private_storage_dir: Path = BACKEND_DIR / '.private_storage'

    @field_validator('allowed_origins', mode='before')
    @classmethod
    def parse_allowed_origins(cls, v: Union[list[str], str]) -> list[str]:
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped.startswith('[') and v_stripped.endswith(']'):
                try:
                    return json.loads(v_stripped)
                except Exception:
                    pass
            return [x.strip() for x in v.split(',') if x.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
