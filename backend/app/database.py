from functools import lru_cache
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


@lru_cache
def get_engine():
    settings = get_settings()
    url = settings.database_url
    if not url:
        raise RuntimeError('Configure a DATABASE_URL before using the database.')

    if url.startswith('postgresql+psycopg://') or url.startswith('postgresql://'):
        return create_engine(url, pool_pre_ping=True)
    elif url.startswith('sqlite:///'):
        return create_engine(url, connect_args={'check_same_thread': False})
    else:
        raise RuntimeError('DATABASE_URL must use postgresql+psycopg:// or sqlite:/// scheme.')


def get_db() -> Generator[Session, None, None]:
    engine = get_engine()
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as session:
        yield session
