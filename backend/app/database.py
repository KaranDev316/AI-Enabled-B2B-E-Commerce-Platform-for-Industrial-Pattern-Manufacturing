from functools import lru_cache

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


@lru_cache
def get_engine():
    url = get_settings().database_url
    if not url.startswith('postgresql+psycopg://'):
        raise RuntimeError('Configure a PostgreSQL psycopg DATABASE_URL before using the database.')
    return create_engine(url, pool_pre_ping=True)


def get_db():
    factory = sessionmaker(bind=get_engine())
    with factory() as session:
        yield session
