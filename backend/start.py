"""Apply pending schema revisions, then replace this process with the API server."""
import argparse
from contextlib import contextmanager
import os
from pathlib import Path
import sys

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from app.config import get_settings

BACKEND = Path(__file__).resolve().parent
MIGRATION_LOCK = 0x4B5043  # KPC: serialize cooperating PostgreSQL startup processes.


@contextmanager
def migration_lock(url):
    if not url.startswith(('postgresql://', 'postgresql+psycopg://')):
        yield
        return
    engine = create_engine(url, poolclass=NullPool)
    try:
        with engine.connect() as connection:
            connection.execute(text('SELECT pg_advisory_lock(:key)'), {'key': MIGRATION_LOCK})
            try:
                yield
            finally:
                connection.execute(text('SELECT pg_advisory_unlock(:key)'), {'key': MIGRATION_LOCK})
    finally:
        engine.dispose()


def migrate():
    url = get_settings().database_url
    if not url:
        raise RuntimeError('Configure DATABASE_URL before starting the backend.')
    config = Config(str(BACKEND / 'alembic.ini'))
    config.set_main_option('script_location', str(BACKEND / 'migrations'))
    print('Checking database migrations…', flush=True)
    with migration_lock(url):
        command.upgrade(config, 'head')
    print('Database is up to date.', flush=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--migrate-only', action='store_true')
    parser.add_argument('--host', default='0.0.0.0' if os.getenv('RENDER') else '127.0.0.1')
    parser.add_argument('--port', type=int, default=int(os.getenv('PORT', '8001')))
    parser.add_argument('--reload', action='store_true', help='Enable local Python reload after the initial migration check.')
    args = parser.parse_args(argv)
    os.chdir(BACKEND)
    # An upgrade failure exits here: no API is started against a stale schema.
    migrate()
    if args.migrate_only:
        return
    command_line = [sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', args.host, '--port', str(args.port)]
    if args.reload:
        command_line.append('--reload')
    os.execv(sys.executable, command_line)


if __name__ == '__main__':
    main()
